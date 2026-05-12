# GPU Worker 기본 리소스

이 디렉터리는 GPU Worker가 cluster에 합류한 뒤 확인해야 할 최소 리소스를 관리합니다.
OpenStack에서 GPU flavor VM을 만들고, Kubernetes node 등록과 NVIDIA runtime 설치가
끝난 다음 적용하는 것을 기준으로 합니다.

## 적용 순서

```sh
kubectl apply -k infra/private-cloud/gpu-worker
```

적용 전 확인할 것:

- GPU node에 `accelerator=nvidia` label을 부여합니다.
- GPU node에 `nvidia.com/gpu=true:NoSchedule` taint를 부여합니다.
- NVIDIA device plugin은 Helm 또는 GitOps로 설치합니다.
- `nvidia-device-plugin-values.example.yaml`은 실제 값이 아닌 출발점입니다.

적용 후 `nvidia-smi-validation` Job으로 GPU runtime 연결 여부를 확인합니다.
