# Argo CD Image Updater Implementation

## 1. 변경 목적

이번 변경의 목적은 Argo CD Image Updater를 현재 레포의 provisioning/GitOps 경로에 편입시키는 것입니다.

배경은 다음과 같습니다.

1. `pdm-serving`의 수동 GitOps 배포는 이미 검증되었습니다.
2. `public/k8s/serving/predictive-model/kustomization.yaml`의 `images[].newTag`를 바꾸면 Argo CD가 이를 감지하고 `pdm-predictor`를 정상 롤링 업데이트합니다.
3. 따라서 자동화에 필요한 핵심은:
   - Image Updater controller 설치
   - private ECR 조회 권한
   - 향후 결정할 Git write-back 자격증명 경로

이번 구현은 KServe ingress/gateway 이슈를 해결하는 작업이 아닙니다. `InferenceService Ready=False`는 여전히 별도 범위입니다.

## 2. 변경된 파일과 역할

### `public/k8s/argocd/apps/argocd-image-updater-app.yaml`

- Argo CD `Application`
- `platform-addons`가 읽는 `public/k8s/argocd/apps` 아래에 등록
- source path:
  - `public/k8s/argocd/addons/argocd-image-updater`
- destination namespace:
  - `argocd`
- sync-wave:
  - `1`

### `public/k8s/argocd/apps/kustomization.yaml`

- 새 `argocd-image-updater-app.yaml` 등록
- 기존 app-of-apps 구조 유지

### `public/k8s/argocd/addons/argocd-image-updater/install-v1.2.1.yaml`

- upstream `argocd-image-updater` 공식 `v1.2.1` install manifest vendoring
- runtime 시 외부 raw URL 의존 제거

### `public/k8s/argocd/addons/argocd-image-updater/kustomization.yaml`

- vendored install manifest를 resource로 포함
- IRSA annotation patch와 최소 config patch를 적용

### `public/k8s/argocd/addons/argocd-image-updater/serviceaccount-irsa-patch.yaml`

- `argocd-image-updater-controller` ServiceAccount에:
  - `eks.amazonaws.com/role-arn`
  annotation 부여

### `public/k8s/argocd/addons/argocd-image-updater/configmap-patch.yaml`

- controller 기본 namespace
- poll interval
- log level/format
- git commit metadata
를 최소 설정으로 추가

### `public/terraform/argocd_image_updater_irsa.tf`

- Image Updater controller용 IAM Role 추가
- trust policy:
  - `system:serviceaccount:argocd:argocd-image-updater-controller`
- ECR 최소 권한:
  - `ecr:GetAuthorizationToken`
  - `ecr:DescribeImages`
  - `ecr:DescribeRepositories`
  - `ecr:ListImages`
  - `ecr:BatchGetImage`

### `public/terraform/outputs.tf`

- `argocd_image_updater_role_arn` output 추가

### `.github/workflows/setup-argocd.yml`

- 이번 단계에서는 PAT 관련 자동화를 넣지 않음
- 기존 Argo CD bootstrap, repo credential, `platform-addons` apply 흐름만 유지

## 3. 설치 구조

전체 구조는 아래와 같습니다.

```text
GitHub Actions setup-argocd.yml
  -> EKS access + kubectl bootstrap
  -> Argo CD repo credential Secret 생성
  -> platform-addons Application apply
    -> argocd-image-updater Application sync
      -> argocd-image-updater-controller 설치
      -> IRSA를 통해 ECR 조회
      -> 기존 write-back-method 설정을 해석
```

## 4. `pdm-serving`과의 연결 방식

`pdm-serving`은 기존 annotation 방식 그대로 유지합니다.

확인한 핵심 annotation:

- `argocd-image-updater.argoproj.io/image-list`
- `argocd-image-updater.argoproj.io/predictive-model.update-strategy`
- `argocd-image-updater.argoproj.io/predictive-model.allow-tags`
- `argocd-image-updater.argoproj.io/predictive-model.force-update`
- `argocd-image-updater.argoproj.io/predictive-model.kustomize.image-name`
- `argocd-image-updater.argoproj.io/write-back-method: git`
- `argocd-image-updater.argoproj.io/write-back-target: kustomization`
- `argocd-image-updater.argoproj.io/git-branch: main`

이번 구현에서는 별도 `ImageUpdater` CR을 추가하지 않습니다.

## 5. 실제 배포 기준 파일

중요한 점은 `pdm-isvc.yaml`의 literal image tag가 최종 기준이 아니라는 점입니다.

실제 기준:

- `public/k8s/serving/predictive-model/kustomization.yaml`

즉 Image Updater가 성공적으로 동작하면:

1. `kustomization.yaml`의 `images[].newTag` 변경
2. Argo CD sync
3. `pdm-predictor` 교체

이 흐름으로 반영됩니다.

## 6. ECR 인증 방식

운영 기본값은 IRSA입니다.

이유:

1. private ECR tag 조회는 장기적으로 static docker-registry secret보다 IRSA가 안전합니다.
2. ECR login password는 만료됩니다.
3. 현재 레포는 이미 Terraform 기반 IRSA 패턴을 사용 중입니다.

이번 구현에서 controller는 `argocd-image-updater-controller` ServiceAccount에 연결된 IAM Role을 통해 `predictive-model` repository의 tag를 조회합니다.

## 7. Git write-back 인증 방식

Git write-back 인증 방식은 이번 단계에서 최종 결정하지 않았습니다.

현재 `pdm-serving`은 아래 annotation을 그대로 유지합니다.

```yaml
argocd-image-updater.argoproj.io/write-back-method: git
```

즉, 현재 코드는 전용 PAT Secret 자동화 없이 기존 write-back-method 상태를 유지합니다.

전용 Secret 방식으로 전환하려면 향후 다음 변경이 필요합니다.

```yaml
argocd-image-updater.argoproj.io/write-back-method: git:secret:argocd/argocd-image-updater-git-creds
```

## 8. PAT 전달 방식 후보와 현재 판단

PAT 적용은 이번 단계에서 보류합니다.

검토 후보는 세 가지입니다.

1. GitHub Actions가 직접 `kubectl`로 Kubernetes Secret 생성
2. GitHub Actions가 SSM Run Command payload에 PAT 직접 전달
3. GitHub Actions가 AWS Secrets Manager 또는 SSM Parameter Store에 PAT를 저장하고, SSM 대상 서버가 이를 읽어 Kubernetes Secret 생성

장단점은 다음과 같습니다.

1. 직접 `kubectl`
   - 장점: 단순함
   - 단점: GitHub runner가 클러스터에 직접 접근 가능한 구조가 필요함
2. SSM payload 직접 전달
   - 장점: 현재 bootstrap 구조에 붙이기 쉬움
   - 단점: 비밀값이 command payload를 직접 통과함
3. Secrets Manager/Parameter Store 경유
   - 장점: 현재 SSM 기반 bootstrap 구조와 가장 잘 맞고 보안상 가장 안전함
   - 단점: 구성 단계가 하나 더 필요함

현재 프로젝트에는 3번이 가장 적합하지만, 이번 단계에서는 실제 구현하지 않습니다.

## 9. ECR IAM User fallback에 대한 판단

GitHub Secrets에는 아래 값도 존재합니다.

- `AWS_ECR_IAM_ID`
- `AWS_ECR_IAM_PASS`

이 값들은 ECR docker-registry secret fallback을 만드는 데 사용할 수는 있습니다.

하지만 이번 구현에서는 workflow에 기본 반영하지 않았고, 운영 자동화 경로에도 포함하지 않았습니다.

이유:

1. 운영 기본값이 IRSA이기 때문
2. ECR login password는 만료되기 때문
3. fallback secret까지 bootstrap에 넣으면 운영 경로가 이중화되어 오히려 진단이 복잡해질 수 있기 때문

필요 시 아래 절차를 수동 또는 별도 workflow로 사용할 수 있습니다.

```bash
AWS_ACCESS_KEY_ID="${AWS_ECR_IAM_ID}" \
AWS_SECRET_ACCESS_KEY="${AWS_ECR_IAM_PASS}" \
AWS_DEFAULT_REGION="ap-northeast-2" \
aws ecr get-login-password --region ap-northeast-2 > /tmp/ecr_password

kubectl -n argocd create secret docker-registry ecr-pull-secret \
  --docker-server=808379768010.dkr.ecr.ap-northeast-2.amazonaws.com \
  --docker-username=AWS \
  --docker-password="$(cat /tmp/ecr_password)" \
  --dry-run=client -o yaml | kubectl apply -f -

rm -f /tmp/ecr_password
```

이 방식은 fallback일 뿐이며 운영 기본값으로 권장하지 않습니다.

## 10. 보안 주의

이번 변경에서 커밋하지 않은 항목:

- `AWS_ECR_IAM_ID` 실제 값
- `AWS_ECR_IAM_PASS` 실제 값
- ECR login password
- 어떤 private key 또는 access token의 실값

레포에는 IAM 정책, patch, workflow 구조 설명, 향후 TODO만 들어갑니다.

## 11. 향후 검증 절차

```bash
kubectl -n argocd get application argocd-image-updater
kubectl -n argocd get deploy,pod | grep -i image
kubectl -n argocd get sa argocd-image-updater-controller -o yaml | grep -A5 eks.amazonaws.com/role-arn
kubectl -n argocd logs deploy/argocd-image-updater-controller --tail=300
kubectl -n argocd logs deploy/argocd-image-updater-controller --tail=500 | egrep -i "pdm-serving|predictive-model|ecr|error|warn|git|commit|push|tag|updated|credentials|auth"
kubectl -n inference get deploy pdm-predictor -o wide
kubectl -n inference get pods -o jsonpath='{range .items[*]}{.metadata.name}{" => "}{.spec.containers[*].image}{"\n"}{end}' | grep pdm-predictor
kubectl -n inference get isvc pdm
```

## 12. 남은 TODO

1. Terraform apply 후 IRSA role ARN과 ServiceAccount annotation 일치 여부 확인
2. Image Updater 로그에서 ECR auth 성공 여부 확인
3. Git write-back 인증 방식을 세 후보 중 하나로 최종 결정
4. 전용 Secret 방식이 확정되면 `pdm-serving`의 `write-back-method`를 `git:secret:argocd/argocd-image-updater-git-creds`로 전환할지 검토
