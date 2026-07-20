# Hybrid AI Serving Platform

하이브리드 클라우드 기반 비동기 AI 서빙 플랫폼 평가 제출용 문서입니다. 이 저장소는 AI 모델 학습부터 이미지 패키징, 하이브리드 전달, 서빙 배포까지 이어지는 **AI Serving Infrastructure**를 중심으로 구성되어 있습니다.

## 1. 프로젝트 개요

Hybrid AI Serving Platform은 **Private Cloud에서 AI 모델 학습/패키징을 수행하고, 검증된 모델 이미지를 Public Cloud의 AWS ECR/EKS/KServe 환경으로 전달하여 서빙하는 하이브리드 AI 서빙 인프라 프로젝트**입니다.

핵심 목적은 다음과 같습니다.

- 민감 데이터와 학습 환경은 Private Cloud에 유지
- Public Cloud에서는 확장 가능한 AI Serving 환경 제공
- 단순 모델 개발이 아니라 모델을 안정적으로 빌드, 전달, 배포, 운영하기 위한 인프라와 자동화 파이프라인 구축
- 민감 데이터 자체는 Public Cloud로 직접 이동하지 않고, **검증된 모델 이미지와 배포 매니페스트 중심으로 전달**

현재 저장소 기준으로는 다음 흐름이 확인됩니다.

- Private Cloud: OpenStack, Private Kubernetes, MinIO, Harbor, GitLab Runner, Argo Events/Workflows 관련 리소스
- Hybrid Bridge: Bastion, Site-to-Site VPN, ECR-over-VPN 전달 스크립트, Slack Alert Relay
- Public Cloud: AWS Terraform, ECR, EKS, ArgoCD, ArgoCD Image Updater, KServe, KEDA, MSK
- SRE: Prometheus, Grafana, Loki, Chaos Mesh, k6, Kafka Exporter

## 2. 아키텍처 다이어그램

본 프로젝트의 전체 하이브리드 아키텍처 원본은 Draw.io 파일로 관리합니다.

- 전체 아키텍처 원본: [`docs/architecture.drawio`](./docs/architecture.drawio)

<!-- TODO: GitHub README 미리보기를 위해 docs/images/architecture-overview.png 또는 docs/images/architecture-overview.svg export 필요 -->

<!-- TODO: 필요 시 아래 세부 아키텍처 다이어그램 추가
- Private Cloud 모델 학습 파이프라인
- Hybrid Image Promotion Pipeline
- Public Cloud Event-Driven Serving Pipeline
- SRE Monitoring / Incident Flow
-->

## 3. 주요 개발 기능

| 구분 | 주요 기능 | 설명 | 관련 기술 |
|---|---|---|---|
| Edge | On-Premise Edge Simulator | 반도체 공장 환경을 모사하는 온프레미스 시뮬레이터로 설비 데이터를 생성하고 AWS 클라우드로 추론 요청을 전달한다. GitHub Actions로 시뮬레이터 이미지를 빌드하고 GHCR에 배포하며, 온프레미스 환경에서 실행되어 공장 설비 데이터 발생을 재현한다. | Docker, Python, GitHub Actions, GHCR, strongSwan, Ubuntu 24.04 LTS |
| Private | Private Cloud Infrastructure | 폐쇄망 환경에서 GPU 모델 학습과 AWS 추론용 이미지 생성 및 전달을 수행하는 내부 운영 인프라다. OpenStack 기반 VM 위에 Kubernetes 클러스터를 구성하고 GPU Node, Control Plane, NFS, MinIO, Argo Workflows, Harbor, GitLab Runner, Kaniko 기반 파이프라인을 운영한다. | OpenStack, Kubernetes, QEMU/KVM, Ubuntu 24.04 LTS, NVIDIA GPU, NFS, MinIO, Argo Workflows, Harbor, GitLab Runner, Kaniko, Trivy |
| Hybrid | Network Bridge / 망연계 서버 | Private Cloud는 공인 IP 없이 폐쇄망을 유지하고, 외부 통신은 망연계 서버를 통해 일원화한다. 데이터 플레인에서는 내부 네트워크 연결, IP Forwarding, IPsec 터널 종단을 담당하고, 관리 플레인에서는 VPN 자동 실행, 구성 파일 생성, 원격 접근 및 동기화를 담당한다. | Docker, GitHub Actions, strongSwan, Tailscale, SSH/rsync |
| Hybrid | Dependency Mirroring | 폐쇄망을 유지하면서 필요한 바이너리와 의존성 파일을 공급하기 위해 미러 저장소를 운영하고 SHA256 기반 무결성 검증을 수행한다. 번들 수집, 1차 검증, 미러 저장, 미러 제공, 패키지 다운로드, 2차 검증, 설치/실행 흐름으로 관리한다. | Mirroring, SHA256 Verification, Offline Bundle Management |
| Model | Model Training Pipeline | MinIO에 업로드된 학습 데이터와 `_SUCCESS` 오브젝트를 기준으로 Argo Workflows가 모델 학습을 수행하고, 결과물은 MinIO artifacts 경로에 저장한다. 이후 inference 코드, requirements, Dockerfile, 모델 파일을 조합해 predictor 이미지를 생성하고 Harbor에 push한다. | MinIO, Argo Workflows, GitLab Runner Pod, Kaniko, Harbor, Python, Dockerfile |
| Hybrid | Hybrid Image Promotion Pipeline | GitLab Runner가 Harbor에서 모델 이미지를 Pull하고 Trivy로 취약점을 검사한 뒤 Bastion 또는 Network Bridge Server를 경유해 AWS ECR로 Push한다. Harbor Pull, Bastion 경유 ECR Push, AWS ECR 적재 및 검증의 3단계로 구성된다. | GitLab Runner, Harbor, Trivy, skopeo, Bastion, NAT/SNAT/Routing, StrongSwan, Site-to-Site VPN, AWS ECR |
| Public | Public Cloud Serving Infrastructure | AWS 상에서 AI Serving 서비스를 운영하고 고객사 추론 요청을 안정적으로 처리하는 외부 서비스 인프라다. EKS Node Group, 3-AZ Multi-AZ 구조, On-Demand + Spot 조합, Cluster Autoscaler, KEDA, KServe 기반 확장 구조를 사용한다. | AWS, Amazon EKS, Amazon ECR, Amazon MSK, Docker, Terraform, GitHub Actions, KEDA, KServe, ArgoCD, Istio, Python, FastAPI |
| Public | Event-Driven Async Architecture | API, Kafka, Worker, PdM 모델을 직접 결합하지 않고 이벤트 기반으로 분리해 트래픽 급증 시 요청을 완충하고 장애를 격리한다. At-Least-Once 처리, Producer Idempotence, `request_id` 기반 제어, DynamoDB 조건부 쓰기, Exponential Backoff, Jitter 기반 재시도를 적용한다. | Kafka / Amazon MSK, KEDA, Worker Pod, DynamoDB, FastAPI |
| Public | High Availability / Scaling Architecture | On-Demand Node Group으로 기본 추론 용량을 확보하고 Spot Node Group으로 급증 트래픽을 비용 효율적으로 수용한다. Inference Worker는 Kafka Lag 기반으로, PdM Predictor는 동시 요청 수 기반으로 확장되며 PDB, Readiness Probe, Liveness Probe를 통해 가용성을 보강한다. 세부 min/max 및 threshold 값은 환경별 상이다. | Amazon EKS, KEDA, KServe, PodDisruptionBudget, Readiness Probe, Liveness Probe, Spot / On-Demand |
| Public | Istio Ambient Mesh Security | 내부 추론 경로에 공통 보안 계층을 적용하기 위해 Sidecar 대신 ztunnel / Waypoint 기반 Ambient Mesh를 도입했다. STRICT mTLS, AuthorizationPolicy, Kubernetes NetworkPolicy를 조합해 내부 접근을 제어한다. | Istio, Ambient Mesh, ztunnel, Waypoint, mTLS, Kubernetes NetworkPolicy |
| Service | Customer Dashboard | 고객사 운영 담당자가 설비별 추론 결과, 정상/고장 상태, 장비별 이상 이력을 확인할 수 있는 대시보드 기능이다. 실제 공개 URL은 README에 직접 쓰지 않으며 필요 시 `<DASHBOARD_URL>` placeholder를 사용한다. | FastAPI, React |
| SRE | Infrastructure / Service Monitoring | 플랫폼 운영 담당자가 클러스터 상태와 서비스 성능을 모니터링한다. Running Pods, Pod Restarts, Targets Up, Node/Pod 자원, Pending Pods, Autoscaling, KEDA/KServe Replica, E2E 지표, Error Rate, Availability, SLO, Error Budget, Kafka Lag, Retry, DLQ 등을 관찰한다. | Prometheus, Grafana, Loki |

본 프로젝트의 주요 개발 범위는 모델 자체의 성능 개선보다, 폐쇄망 기반 모델 학습·패키징 환경과 퍼블릭 클라우드 기반 실시간 추론 서빙 환경을 안정적으로 연결하는 인프라 파이프라인 구축에 초점을 둔다.

Private Cloud는 데이터 보안과 모델 생성/패키징을 담당하고, Public Cloud는 대규모 추론 요청 처리와 탄력적인 스케일링을 담당하도록 역할을 분리했다.

Kafka/KEDA 기반 Event-Driven 구조를 통해 API, Worker, Predictor를 분리하고, 트래픽 완충·장애 격리·독립 확장이 가능한 구조를 구현했다.

## 4. 사용 기술 스택 및 버전

| 분류 | 기술 | 버전/비고 | 역할 |
|---|---|---|---|
| Private Cloud | OpenStack | Terraform provider `~> 3.4`, 플랫폼 버전은 환경별 상이 | Private VM 및 네트워크 기반 인프라 |
| Container Platform | Kubernetes | Private 기본값 `v1.36` (`.env.example`), EKS 기본값 `1.31` (`public/terraform/variables.tf`) | 학습/서빙 워크로드 오케스트레이션 |
| SCM / CI | GitLab | GitLab CE `18.11.4-ce.0` (`private/ci/private-cloud-apply.sh`) | Private 소스 관리 및 CI 진입점 |
| Runner | GitLab Runner | Helm chart `0.89.1` (`private/gitlab-runner/README.md`) | Kubernetes executor 기반 파이프라인 실행 |
| Eventing | Argo Events | 문서 기준 | MinIO 이벤트 기반 트리거 |
| Workflow | Argo Workflows | 문서 기준 | 모델 학습, 패키징, 후속 전달 |
| Registry | Harbor | 환경별 상이 | Private 이미지 저장 및 검증 |
| Object Storage | MinIO | `RELEASE.2024-05-10T01-41-38Z` | 데이터셋/아티팩트 저장 |
| Image Build | Kaniko | `v1.23.2-debug` | 모델 서빙 이미지 빌드 |
| Security Scan | Trivy | 환경별 상이 | 이미지 보안 점검 |
| Public Registry | AWS ECR | 관리형 서비스 | Public 배포용 이미지 저장소 |
| Public Cluster | AWS EKS | 클러스터 버전 기본값 `1.31` | Public 서빙 클러스터 |
| Model Serving | KServe | Helm chart `v0.17.0`, ISVC API `serving.kserve.io/v1beta1` | 모델 추론 서빙 |
| GitOps | ArgoCD | Helm chart 변수 `7.8.23` | Public 배포 동기화 |
| Image Automation | ArgoCD Image Updater | 저장소 내 addon 구성, 버전은 환경별 상이 | ECR 태그 감지 및 GitOps 연계 |
| Network Bridge | StrongSwan | 환경별 상이 | Site-to-Site VPN 구성 |
| Hybrid Connectivity | Site-to-Site VPN | AWS VPN + Private 연동 | Private → Public 전송 경로 |
| Async Messaging | Kafka / AWS MSK | MSK Kafka `3.9.x` | 비동기 추론 요청 큐 |
| Event Scaling | KEDA | Helm chart `2.19.0` | Kafka lag 기반 오토스케일 |
| Monitoring | Prometheus | kube-prometheus-stack 사용, 버전은 환경별 상이 | 메트릭 수집 및 알림 |
| Visualization | Grafana | Helm chart 사용, 버전은 환경별 상이 | 대시보드 시각화 |
| Alert Relay | Slack Alert Relay | 저장소 내 FastAPI 기반 커스텀 이미지 | Private 이벤트를 Slack으로 중계 |

## 5. 디렉토리 구조

실제 저장소를 기준으로 핵심 구조만 정리하면 다음과 같습니다.

```bash
.
├── README.md
├── .env.example
├── .env.secret.example
├── .github/
│   └── workflows/
├── ha
├── private/
│   ├── aws-oidc/
│   ├── ci/
│   ├── gitlab-runner/
│   ├── gpu-worker/
│   ├── handoff/
│   ├── kubernetes/
│   │   └── model-build-workflows/
│   ├── kubernetes-bootstrap/
│   ├── openstack/
│   ├── openstack-kolla/
│   ├── openstack-local/
│   ├── reverse-proxy/
│   ├── storage/
│   └── templates/
├── public/
│   ├── k8s/
│   │   ├── apps/
│   │   ├── argocd/
│   │   ├── base/
│   │   ├── policy/
│   │   └── serving/
│   ├── terraform/
│   └── terraform-incluster/
├── services/
│   ├── dashboard-backend/
│   ├── dashboard-frontend/
│   ├── inference-api/
│   └── inference-worker/
├── infra-alert-images/
│   ├── alert-relay/
│   └── notify-runner/
├── sre/
│   └── k6/
├── sre-monitoring/
│   ├── chaos/
│   ├── chaos-mesh/
│   ├── grafana/
│   ├── k6/
│   ├── kafka-exporter/
│   ├── loki/
│   ├── prometheus/
│   └── scripts/
├── edge/
└── temp/
```

## 6. 실행 및 배포 방법

### 사전 준비

- Kubernetes cluster 접근 권한
- `kubectl`
- GitLab Runner 또는 GitHub Actions 실행 환경
- `aws` CLI
- AWS ECR Repository
- ArgoCD
- 필요한 Kubernetes Namespace (`model-build`, `argo-events`, `inference`, `argocd`, `monitoring` 등)
- VPN/Bastion 네트워크 연결

### 모델 빌드/학습 Workflow 실행

현재 저장소 기준 핵심 Workflow 경로:

- `private/kubernetes/model-build-workflows/workflowtemplates.yaml`
- `private/kubernetes/model-build-workflows/minio-event-sensor.yaml`
- `private/kubernetes/model-build-workflows/eventbus.yaml`
- `private/kubernetes/model-build-workflows/kustomization.yaml`

배포 예시:

```bash
kubectl apply -k private/kubernetes/model-build-workflows
```

수동 실행 예시:

```bash
argo submit -n model-build \
  --from workflowtemplate/model-build-job \
  -p image_tag=v1.0.0 \
  -p dataset_object_key=raw-data/dev/_SUCCESS
```

참고:

- 기본 파라미터 예시는 `workflowtemplates.yaml`에 정의되어 있습니다.
- `DATASET_OBJECT_KEY`는 `raw-data/<version>/_SUCCESS` 형식을 사용합니다.
- MinIO 이벤트 기반 자동 실행은 `argo-events` 리소스가 선행 배포되어야 합니다.

### GitLab CI/CD 실행

현재 저장소 상태 기준:

- GitLab Runner 구성: `private/gitlab-runner/`
- 모델 전달 설계 문서: `private/handoff/model-build-delivery.md`
- ECR-over-VPN 검증 스크립트: `private/ci/model-build-vpn-ecr-pipeline-mock.sh`
- 루트 `.gitlab-ci.yml`: 현재 저장소에 없음

따라서 평가 문서 기준 실행 흐름은 다음처럼 정리할 수 있습니다.

1. GitLab 프로젝트에 모델 코드와 `.gitlab-ci.yml`을 구성한다.  
2. `model-build` 태그를 가진 Runner가 Job을 수신한다.  
3. Runner가 Argo Workflow 실행 또는 Harbor → ECR 전달 단계를 호출한다.  

파라미터 예시:

```env
IMAGE_TAG=v1.0.0
DATASET_OBJECT_KEY=raw-data/dev/_SUCCESS
AWS_REGION=ap-northeast-2
ECR_REPOSITORY=predictive-model
```

현재 저장소에는 GitLab CI의 완성된 루트 파이프라인 대신, **Runner 구성과 handoff 문서, mock 스크립트가 준비된 상태**입니다.

보조적으로 실제 저장소에는 GitHub Actions 기반 Public 배포 자동화가 존재합니다.

- `.github/workflows/inference-image-build.yml`
- `.github/workflows/public-terraform-deploy.yml`
- `.github/workflows/setup-argocd.yml`

### ECR 이미지 확인

```bash
aws ecr describe-images \
  --repository-name predictive-model \
  --region ap-northeast-2
```

### ArgoCD 배포 확인

```bash
kubectl get application -n argocd
kubectl get isvc -n inference
kubectl get pods -n inference
```

### KServe 서비스 확인

현재 저장소 기준 InferenceService 이름은 `pdm`입니다.

```bash
kubectl get inferenceservice -n inference
kubectl get inferenceservice pdm -n inference
kubectl get pods -n inference
kubectl get svc -n inference
```

참고:

- `public/k8s/serving/predictive-model/pdm-isvc.yaml` 기준으로 Predictor 이미지가 연결됩니다.
- 실제 KServe가 생성한 Service 이름은 배포 환경별로 확인이 필요합니다.

## 7. 환경 변수 설정 방법

### 환경 변수 표

| 변수명 | 예시 | 사용 위치 | 설명 |
|---|---|---|---|
| `AWS_REGION` | `ap-northeast-2` | GitLab CI/CD Variables, Local `.env` | AWS 리전 |
| `AWS_ACCOUNT_ID` | `<YOUR_AWS_ACCOUNT_ID>` | GitLab CI/CD Variables, Local `.env` | AWS 계정 ID |
| `ECR_REGISTRY` | `<YOUR_AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com` | GitLab CI/CD Variables, Local `.env` | ECR 레지스트리 주소 |
| `ECR_REPOSITORY` | `predictive-model` | GitLab CI/CD Variables | 배포 대상 ECR 저장소 |
| `IMAGE_TAG` | `v1.0.0` | GitLab CI/CD Variables, Argo Workflow Parameters | 이미지 태그 |
| `HARBOR_REGISTRY` | `harbor.example.local` | GitLab CI/CD Variables, Argo Workflow Parameters | Private Harbor 주소 |
| `HARBOR_PROJECT` | `models` | GitLab CI/CD Variables, Argo Workflow Parameters | Harbor 프로젝트명 |
| `MINIO_ENDPOINT` | `http://<MINIO_ENDPOINT>` | Argo Workflow Parameters, Local `.env` | MinIO 접속 주소 |
| `MINIO_ACCESS_KEY` | `<YOUR_MINIO_ACCESS_KEY>` | Kubernetes Secret, Local `.env` | MinIO 액세스 키 |
| `MINIO_SECRET_KEY` | `<YOUR_MINIO_SECRET_KEY>` | Kubernetes Secret, Local `.env` | MinIO 시크릿 키 |
| `DATASET_OBJECT_KEY` | `raw-data/<version>/_SUCCESS` | Argo Workflow Parameters, GitLab CI/CD Variables | 학습 트리거 대상 데이터셋 객체 |
| `GITLAB_TRIGGER_TOKEN` | `<YOUR_GITLAB_TRIGGER_TOKEN>` | GitLab CI/CD Variables | GitLab trigger token |
| `GITLAB_PROJECT_ID` | `<YOUR_GITLAB_PROJECT_ID>` | GitLab CI/CD Variables | GitLab 프로젝트 ID |
| `GITOPS_REPO_URL` | `https://github.com/<org>/<repo>.git` | GitLab CI/CD Variables, ArgoCD 설정 | GitOps 저장소 주소 |
| `GITOPS_BRANCH` | `main` | GitLab CI/CD Variables | GitOps 반영 브랜치 |
| `ARGOCD_APP_NAME` | `pdm-serving` | GitLab CI/CD Variables, Local `.env` | ArgoCD 애플리케이션 이름 |
| `RELAY_URL` | `http://<BASTION_HOST>:8081/ci-event` | Bastion / Relay 설정, GitLab CI/CD Variables | Alert relay 엔드포인트 |
| `RELAY_TOKEN` | `<YOUR_RELAY_TOKEN>` | Bastion / Relay 설정, GitLab CI/CD Variables | Relay 인증 토큰 |
| `SLACK_WEBHOOK_URL` | `<YOUR_SLACK_WEBHOOK_URL>` | Bastion / Relay 설정 | Slack Webhook URL |

### `.env.example` 예시

```env
AWS_REGION=ap-northeast-2
AWS_ACCOUNT_ID=<YOUR_AWS_ACCOUNT_ID>
ECR_REGISTRY=<YOUR_AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com
ECR_REPOSITORY=predictive-model
IMAGE_TAG=v1.0.0

HARBOR_REGISTRY=harbor.example.local
HARBOR_PROJECT=models

MINIO_ENDPOINT=http://<MINIO_ENDPOINT>
MINIO_ACCESS_KEY=<YOUR_MINIO_ACCESS_KEY>
MINIO_SECRET_KEY=<YOUR_MINIO_SECRET_KEY>
DATASET_OBJECT_KEY=raw-data/<version>/_SUCCESS

GITLAB_PROJECT_ID=<YOUR_GITLAB_PROJECT_ID>
GITLAB_TRIGGER_TOKEN=<YOUR_GITLAB_TRIGGER_TOKEN>

GITOPS_REPO_URL=https://github.com/<org>/<repo>.git
GITOPS_BRANCH=main
ARGOCD_APP_NAME=pdm-serving

RELAY_URL=http://<BASTION_HOST>:8081/ci-event
RELAY_TOKEN=<YOUR_RELAY_TOKEN>
SLACK_WEBHOOK_URL=<YOUR_SLACK_WEBHOOK_URL>
```

### 환경 변수 관리 원칙

- Private CI/CD Variables: GitLab Trigger, Harbor, MinIO, ECR 전달 파라미터, Relay URL/Token
- Public CI/CD Variables: GitHub Actions 또는 Public 배포 파이프라인에서 사용하는 AWS Region, ECR Registry, EKS/ArgoCD 연계 변수
- Kubernetes Secret: MinIO Access Key, MinIO Secret Key, GitLab Repo Token, Harbor 인증 정보, Public 배포 시 필요한 애플리케이션 Secret
- Argo Workflow Parameters: `image_tag`, `dataset_object_key`, `git_repo_url`, `minio_endpoint` 등 모델 빌드/패키징 파라미터
- ArgoCD / GitOps 설정값: 애플리케이션 이름, 대상 브랜치, 이미지 태그 추적 기준 등 배포 선언 정보
- Local `.env`: 로컬 검증 또는 `ha` CLI 실행 시 사용
- Bastion / Relay 설정: `RELAY_URL`, `RELAY_TOKEN`, `SLACK_WEBHOOK_URL`

Public Cloud 관점 관리 기준:

- AWS 인증 정보는 로컬 파일에 직접 두기보다 GitHub Actions Secret 또는 클러스터/IAM Role 연계 방식으로 관리
- ECR, EKS, ArgoCD 관련 값은 Public 배포 파이프라인과 GitOps 매니페스트에서 일관되게 참조
- Kubernetes 내부 애플리케이션 Secret은 Public 클러스터 네임스페이스 단위로 분리 관리
- ArgoCD Image Updater 연계에 필요한 저장소 접근 정보와 GitHub App 정보는 Public 배포 기준 Secret Store 또는 CI Secret에서 관리

주의:

- `SLACK_WEBHOOK_URL`은 GitLab Job이나 Workflow Pod에 직접 넣지 않고 Bastion/Relay 측에만 둡니다.
- 실제 Secret 값은 저장소에 커밋하지 않습니다.

## 8. GitHub 저장소 관리 및 평가자 접근 안내

이 저장소는 코드, Kubernetes Manifest, 인프라 설정, 운영 스크립트, 배포 문서를 **GitHub 저장소에서 통합 관리**하는 구조입니다.

평가자 접근 안내:

- Private Repository라면 평가자 GitHub 계정에 **Read 권한**을 부여해야 합니다.
- README 기준으로 저장소를 탐색하면 Private, Public, Hybrid, SRE 구성을 한 번에 확인할 수 있습니다.
- 현재 저장소는 GitHub Actions 기반 자동화 파일이 포함되어 있으며, GitLab CI는 Runner/문서 중심으로 준비되어 있습니다.

평가자가 우선 확인할 핵심 경로:

| 경로 | 확인 포인트 |
|---|---|
| `README.md` | 프로젝트 전체 개요 및 제출 문서 |
| `.github/workflows/` | Public Terraform, ArgoCD, 이미지 빌드 자동화 |
| `private/ci/` | Private 적용 및 ECR-over-VPN 전달 스크립트 |
| `private/gitlab-runner/` | GitLab Runner 구성 |
| `private/kubernetes/model-build-workflows/` | MinIO 이벤트, Argo Workflow 템플릿 |
| `private/storage/` | MinIO 및 스토리지 기준 |
| `private/handoff/` | Hybrid 전달 및 운영 인계 문서 |
| `public/terraform/` | AWS ECR/EKS/MSK/VPN 인프라 코드 |
| `public/k8s/argocd/` | ArgoCD GitOps 애플리케이션 |
| `public/k8s/serving/predictive-model/` | KServe InferenceService 매니페스트 |
| `services/` | inference-api, inference-worker, dashboard 서비스 코드 |
| `infra-alert-images/` | Slack Alert Relay 이미지 구성 |
| `sre-monitoring/` | Prometheus, Grafana, Loki, Chaos, Kafka Exporter |

참고:

- `docs/` 및 `docs/images/`는 현재 저장소 루트에 존재하지 않습니다.
- 루트 `.gitlab-ci.yml`도 현재 저장소에는 없습니다.

## 9. 시연 영상 안내

- 시연 영상은 YouTube 비공개 링크 또는 클라우드 저장소 링크로 제공합니다.
- 영상은 프로젝트 핵심 기능 중심으로 구성합니다.
- 아직 링크가 없다면 placeholder로 둡니다.

- 시연 영상 링크: `<YouTube 비공개 링크 또는 클라우드 저장소 링크 입력>`

### 시연 구성

1. MinIO 데이터 업로드 및 이벤트 발생
2. Argo Events / Workflow 기반 모델 빌드
3. GitLab CI/CD 파이프라인 실행
4. Harbor 또는 ECR 이미지 저장 확인
5. Bastion / VPN 경유 ECR Push 확인
6. ArgoCD Image Updater 기반 GitOps 반영
7. KServe Predictor Pod 배포 및 이미지 교체 확인
8. 장애 발생 시 Slack Alert Relay 알림 확인

## 10. 팀 역할

| 이름 | 역할 | 담당 영역 | 주요 기술 |
|---|---|---|---|
| 김세원 | 팀장 · Public | AWS Public Cloud 및 비동기 처리 영역 | AWS, EKS, Kafka |
| 문경호 | 팀원 · Private | Private Cloud 및 내부 인프라 영역 | OpenStack, Bastion |
| 신민석 | 팀원 · SRE | 관측성, 장애 검증, 신뢰성 확보 | Monitoring, Chaos |
| 안예원 | 팀원 · Model | 모델 빌드 및 패키징 영역 | Model Build, Package |
| 정승민 | 팀원 · Hybrid | 하이브리드 전달 및 배포 자동화 영역 | GitLab, ArgoCD |

정승민 담당 설명:

- Hybrid Delivery
- CI/CD Bridge
- GitLab Runner 기반 파이프라인
- Private → Public 이미지 전달
- ECR Push
- ArgoCD / ArgoCD Image Updater 연계
- GitOps 기반 배포 자동화

## 11. 트러블슈팅 및 운영 포인트

| 구분 | 문제 상황 | 원인 | 해결 과정 | 결과 / 회고 |
|---|---|---|---|---|
| Private Cloud | 재배포 중 GPU Worker VM이 반복적으로 실패했고, VM 재시작만으로는 복구되지 않았다. 게스트 OS 내부 문제만으로 보기 어려운 장애였다. | GPU Passthrough 환경에서 GPU가 PCI 버스에서 이탈하는 Xid 154 "Fallen off the bus" 장애가 발생했다. 호스트 PCI 계층, 디바이스/브리지 토폴로지, FLR 가능 여부, vfio 바인딩 상태까지 함께 확인해야 하는 문제였다. | 호스트 PCI 계층에 진입해 디바이스 및 브리지 토폴로지를 확인하고 FLR과 링크 복구를 점검했다. 상위 브리지 기준 SBR까지 시도한 뒤 동일 패턴이 재현되는 것을 확인했고, 소비자 GPU reset 한계로 판단해 콜드 리부트를 수행했다. 이후 vfio 재바인딩과 VM 자동 기동 절차를 systemd로 자동화했다. | 재부팅 이후에도 vfio 바인딩과 VM 기동이 자동화되어 재발 시 수동 개입을 줄일 수 있게 됐다. 또한 가상화 환경 장애를 호스트 계층과 게스트 계층으로 분리해 진단하는 운영 경험을 확보했다. |
| Public Cloud | Istio Ambient Mesh 적용 후 `inference-worker -> pdm-predictor` HTTP 호출이 실패했고, `Connection reset by peer`가 발생했다. Pod, ALB, Kafka 등 주요 리소스는 정상이었지만 내부 Pod 간 통신 단절로 추론 결과 적재 실패와 DLQ 발생으로 이어졌다. | Ambient 환경에서 AuthorizationPolicy를 ServiceAccount principals 단위로 좁혀 제한한 기존 정책이 실제 dataplane인 ztunnel/HBONE 경로와 정상적으로 매칭되지 않아 모든 트래픽이 차단됐다. | Ambient 순정 상태를 기준점으로 두고 보안 정책을 bottom-up 방식으로 순차 검증했다. Ambient Dataplane 단독과 STRICT mTLS는 정상, ServiceAccount 기반 AuthorizationPolicy 추가 시 실패를 확인했고, 이후 허용 범위를 ServiceAccount 단위에서 Namespace 단위로 조정해 `namespaces: [inference]` 기준으로 변경했다. NetworkPolicy는 유지한 상태로 검증을 마무리했다. | Ambient + STRICT mTLS + NetworkPolicy 보안 구성은 유지하면서 Worker와 Predictor 간 통신을 복구했고, AI 추론 파이프라인을 정상화했다. 또한 보안 정책은 단순 완화가 아니라 Ambient dataplane 경로와 맞는 단위로 조정해야 한다는 운영 기준을 확보했다. |

## 12. 평가자 확인 체크리스트

- [ ] GitHub 저장소 접근 권한 확인
- [ ] README.md 프로젝트 개요 확인
- [ ] `docs/architecture.drawio` 참조 경로 확인
- [ ] 기술 스택 및 버전 확인
- [ ] 디렉토리 구조 확인
- [ ] 실행 및 배포 방법 확인
- [ ] 환경 변수 설정 방법 확인
- [ ] 시연 영상 링크 확인
- [ ] 주요 Manifest / Workflow / Terraform 경로 확인
- [ ] GitLab Runner / Argo Workflow / ECR-over-VPN / ArgoCD / KServe 흐름 확인

## 부록: 제출 문서 작성 메모

- 전체 아키텍처 원본 참조는 `docs/architecture.drawio` 기준으로 정리했습니다.
- README 미리보기용 PNG/SVG export 파일은 아직 없어 TODO로 남겼습니다.
- 현재 저장소에는 루트 `.gitlab-ci.yml`이 없어 GitLab CI/CD는 Runner 및 handoff 문서 기준으로 설명했습니다.
- 실제 저장소에 존재하지 않는 경로는 확정적으로 쓰지 않았으며, 확인이 어려운 항목은 `환경별 상이` 또는 `문서 기준`으로 표기했습니다.
