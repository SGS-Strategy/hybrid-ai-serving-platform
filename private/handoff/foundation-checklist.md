# Foundation Checklist

이 체크리스트는 Private Cloud Foundation의 공개 가능한 준비 범위만 기록합니다.

## 범위

- OpenStack VM group 계획 확인
- Kubernetes node role 계획 확인
- Storage/MinIO/NFS 계획 확인
- GPU worker 기본 구성 확인
- GitLab/GPU SSH runner 경계 확인
- Harbor VM과 Argo/Kaniko Kubernetes 배치 계획 확인

## 목표 기준

```text
VM:
  control-plane 1
  build-worker 1
  gpu-worker 1
  gitlab 1
  harbor 1

Kubernetes:
  storage
  model-build
  gpu-workload
  argo
```
