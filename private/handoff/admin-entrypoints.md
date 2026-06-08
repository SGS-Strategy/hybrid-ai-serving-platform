# Admin Entrypoints Plan

이 문서는 관리자 진입점의 계획만 기록합니다.

## 대상

| 대상 | 역할 |
| --- | --- |
| OpenStack Horizon | VM, network, image, flavor 관리 |
| GitLab | 코드 저장소와 CI/CD 관리 |
| Kubernetes UI | cluster 상태 확인 |
| Grafana | monitoring UI |
| ArgoCD | GitOps UI |
| Argo Workflows | model build/package workflow 관리 |
| Harbor VM | private image registry 관리 |

## Reverse Proxy 계획

관리자 UI는 물리 서버의 reverse proxy를 통해 내부 서비스로 연결합니다. DNS, TLS, upstream, 인증 정보는 공개 문서에 기록하지 않습니다.
