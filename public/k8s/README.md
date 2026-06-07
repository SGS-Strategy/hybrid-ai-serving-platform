# Kubernetes manifests

This directory contains Kubernetes manifests for application workloads deployed to EKS.

## Structure

- `base/namespace.yaml`: shared namespace
- `apps/inference-api`: API server manifests
- `apps/inference-worker`: worker manifests
- `apps/kserve-predictor`: predictor manifests
- `apps/inference-api/targetgroupbinding.yaml`: binds the inference API service to the Terraform-managed internal ALB target group

## Apply example

```powershell
kubectl apply -f public/k8s/base/namespace.yaml
kubectl apply -f public/k8s/apps/inference-api
kubectl apply -f public/k8s/apps/inference-worker
kubectl apply -f public/k8s/apps/kserve-predictor
```

If you use the Terraform-managed internal ALB, also apply:

```powershell
kubectl apply -f public/k8s/apps/inference-api/targetgroupbinding.yaml
```
