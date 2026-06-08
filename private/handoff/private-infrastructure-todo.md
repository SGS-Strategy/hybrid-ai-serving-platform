# Private Infrastructure TODO

현재 구현은 local/DevStack 기반 Private Cloud Foundation MVP입니다. 아래 항목은 production 수준으로 확장하기 위한 계획입니다.

## 1. Production OpenStack

- 운영용 OpenStack 배포 방식 선택
- 운영 Keystone/project/user 기준 확정
- Terraform state backend 운영화
- Network, subnet, router, security group, key pair, VM 생성 결과 검증
- Terraform output 기반 inventory handoff 기준 정리

## 2. Multi-node Kubernetes

- Control-plane/worker 역할 분리
- Control-plane HA 구성
- Build-worker와 GPU-worker label/taint 기준 확정
- Kubeconfig 보관/전달 정책 확정

## 3. Storage

- Production 기본 storage 선택
- Default StorageClass 기준 확정
- Model artifact/build cache PVC backing 검증
- Backup/restore와 snapshot 보존 정책 정리

## 4. GPU Worker

- GPU flavor/quota 기준 확정
- NVIDIA driver/container runtime/device plugin 기준 확정
- GPU node label/taint 기준 확정
- GPU validation 결과 보관 기준 확정

## 5. 운영 기본 구성

- IngressClass와 ingress controller 구성
- cert-manager와 인증서 발급 방식 구성
- Monitoring/logging baseline 구성
- Production readiness 기준 확대

## 6. Model Build/Package Platform

- Harbor baseline은 별도 영속 VM과 최소 registry profile 기준으로 구성
- Harbor registry data는 `/data/harbor` 기준으로 보존
- Harbor project baseline: `infra`, `models`
- Harbor production hardening: TLS 내부 인증서, backup/restore, retention/garbage collection 정책 확정
- Harbor image cleanup은 retention/garbage collection 정책 확정 후 단계적으로 적용
- Argo Workflows와 `model-build-job` / `model-package-job` baseline은 K8s manifest 기준으로 구성
- MinIO event 또는 GitLab CI 기반 Workflow 제출 trigger 기준 확정
- Workflow 결과 manifest/image tag 기록 정책 확정
- Kaniko는 별도 VM이 아니라 K8s 일회성 Job/Pod로 실행
- Harbor/GitLab/MinIO secret과 serviceAccount/RBAC 기준 확정

## 7. 역할 간 인계

- Model Packaging 담당자에게 namespace, storage, build service account, registry 기준 전달
- Hybrid Delivery 담당자에게 runner, image promotion, manifest 변경 기준 전달
- Public Cloud 담당자에게 public registry/image promotion 기준 전달
