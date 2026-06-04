# Storage 기본 리소스

이 디렉터리는 Private Kubernetes에서 model build cache와 model artifact를 다루기 위한
storage 기본 리소스를 관리합니다. GitHub Actions storage 단계는 Helm으로 MinIO Operator,
local-path provisioner, NFS subdir external provisioner를 설치한 뒤 PVC 예시를 적용합니다.

## 적용 순서

```sh
kubectl apply -k private/storage
```

적용 전 확인할 것:

- `nfs-provisioner-values.yaml`의 NFS server 값은 GitHub Actions에서 Terraform output으로 치환합니다.
- `minio-operator-values.yaml`은 MinIO Operator Helm chart 값입니다.
- MinIO 값은 `minio-values.example.yaml`을 기준으로 별도 secret 관리 체계에서 주입합니다.
- access key, secret key, 내부 endpoint, bucket credential은 커밋하지 않습니다.
