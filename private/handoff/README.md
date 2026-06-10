# Private Cloud Handoff

이 디렉터리는 Private Cloud Foundation에서 다음 담당자에게 넘길 운영 기준을 정리합니다.

## 문서

| 항목 | 전달 대상 |
| --- | --- |
| `github-actions-env.md` | GitHub Actions controller, reusable executor, 변수와 secret 기준 |
| `model-build-delivery.md` | GitLab Runner, Argo model build/package, Harbor, ECR 전달 흐름 |

## 현재 인프라 기준

| 영역 | 기준 |
| --- | --- |
| OpenStack | `control-plane`, `build-worker`, `gpu-worker`, `gitlab`, `harbor` VM 1대씩 |
| Kubernetes | `private-infra`, `private-storage`, `model-build`, `gpu-workload`, `argo` namespace |
| Storage | NFS RWX StorageClass `private-nfs-rwx`, MinIO tenant, `model-build-cache`, `model-artifacts` PVC |
| GitLab | 코드 저장소와 CI/CD 제어면. Runner token은 GitLab VM bootstrap이 생성 |
| Harbor | private registry. `infra`, `models` project와 Kaniko robot account를 bootstrap |
| Argo Workflows | `model-build-job`, `model-package-job` WorkflowTemplate 기준 |
| Public cloud | ECR repository는 `public/terraform`의 `ecr_repositories` 기준으로 생성 |

## 관리자 진입점

관리자 UI는 reverse proxy/DNS를 통해 노출합니다. 주소와 credential은 공개 handoff 문서에 직접 쓰지 않습니다.

| 대상 | 역할 |
| --- | --- |
| OpenStack Horizon | VM, network, image, flavor 관리 |
| GitLab | 코드 저장소, pipeline, runner 관리 |
| Harbor | private image registry, robot account, image retention 관리 |
| Argo Workflows | model build/package workflow 조회와 재실행 |
| Grafana | monitoring UI |
| Kubernetes UI | cluster 상태 확인 |
