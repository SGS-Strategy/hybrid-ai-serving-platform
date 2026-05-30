# Inference Services

This directory contains containerized application code for the four workloads
deployed into the `inference` namespace.

Official container images should be built and pushed by GitHub Actions rather
than from a developer workstation. Local `docker build` is still useful for
fast debugging, but the authoritative images should come from CI and be pushed
to ECR with the commit SHA tag.

## Services

- `inference-api`: public-facing HTTP API that forwards inference requests to the predictor
- `inference-worker`: background worker placeholder for Kafka request processing
- `result-consumer`: background worker placeholder for Kafka result processing
- `kserve-predictor`: model-serving HTTP service compatible with simple JSON inference calls

## Local build

```powershell
docker build -t inference-api:local services/inference-api
docker build -t inference-worker:local services/inference-worker
docker build -t result-consumer:local services/result-consumer
docker build -t kserve-predictor:local services/kserve-predictor
```

## ECR push example

```powershell
aws ecr get-login-password --region ap-northeast-2 |
  docker login --username AWS --password-stdin 808379768010.dkr.ecr.ap-northeast-2.amazonaws.com

docker build -t 808379768010.dkr.ecr.ap-northeast-2.amazonaws.com/inference-api:latest services/inference-api
docker push 808379768010.dkr.ecr.ap-northeast-2.amazonaws.com/inference-api:latest
```

Repeat the same pattern for `inference-worker`, `result-consumer`, and `kserve-predictor`.

## GitHub Actions

The workflow at `.github/workflows/inference-images.yml` is the intended
production path.

- Pull requests build all four service images for validation only.
- Pushes to `main` build and push immutable `${GITHUB_SHA}` tags to ECR.
- Pushes to `main` also refresh the mutable `latest` tag for compatibility with
  the current Kubernetes manifests.

To activate the workflow, add the repository secret
`AWS_GITHUB_ACTIONS_ROLE_ARN` with an IAM role that trusts GitHub OIDC and has
permission to push to the four ECR repositories.
