# Argo CD Image Updater

This addon installs Argo CD Image Updater into the existing `platform-addons` app-of-apps structure and prepares private ECR access through IRSA.

## Scope of the current implementation

Implemented in the current code:

- Argo CD `Application` for Image Updater
- vendored `v1.2.1` install manifest
- IRSA patch for `argocd-image-updater-controller`
- Terraform IAM role and ECR read policy for the controller
- minimal controller `ConfigMap` patch

Explicitly **not** implemented in the current code:

- GitHub PAT to Kubernetes Secret automation
- `argocd-image-updater-git-creds` Secret creation
- `write-back-method: git:secret:...` migration
- ECR IAM User based docker-registry Secret automation

## Installation structure

```text
platform-addons
  -> public/k8s/argocd/apps
    -> argocd-image-updater-app.yaml
      -> public/k8s/argocd/addons/argocd-image-updater
        -> install-v1.2.1.yaml
        -> serviceaccount-irsa-patch.yaml
        -> configmap-patch.yaml
```

## Why this addon exists

Manual GitOps deployment for `pdm-serving` has already been validated:

1. update `public/k8s/serving/predictive-model/kustomization.yaml`
2. Argo CD detects the Git change
3. Argo CD syncs
4. `pdm-predictor` rolls to the new image

So the missing piece for automation was the Image Updater controller itself, not the Kustomize-based deployment path.

## Effective deployment file

For `pdm-serving`, the real image update target is:

- `public/k8s/serving/predictive-model/kustomization.yaml`

not:

- `public/k8s/serving/predictive-model/pdm-isvc.yaml`

That means Image Updater should ultimately change `images[].newTag` in the `kustomization.yaml` file.

## ECR authentication

The default and intended ECR authentication model is IRSA.

Why:

1. ECR login tokens expire.
2. Static docker-registry secrets are awkward to rotate.
3. This repository already uses Terraform-managed IRSA patterns.

The controller ServiceAccount name expected by the install manifest is:

- `argocd-image-updater-controller`

The IRSA trust subject is:

- `system:serviceaccount:argocd:argocd-image-updater-controller`

The Terraform policy grants:

- `ecr:GetAuthorizationToken` on `*`
- `ecr:DescribeImages`
- `ecr:DescribeRepositories`
- `ecr:ListImages`
- `ecr:BatchGetImage`

Repository-scoped ECR access is limited to:

- `predictive-model`

## ECR IAM User fallback

The repository secrets `AWS_ECR_IAM_ID` and `AWS_ECR_IAM_PASS` are **not** used in the current automation path.

They should be treated only as a fallback/manual option because:

1. they reintroduce static credentials into the path
2. they still rely on expiring ECR login tokens
3. they are inferior to IRSA for normal operation

If needed, that path should remain documented as a manual or exceptional fallback, not the default bootstrap behavior.

## Git write-back status

Git write-back is **not finalized** in this stage.

The current `pdm-serving` annotation remains:

```yaml
argocd-image-updater.argoproj.io/write-back-method: git
```

This means the current setup continues to rely on the existing Argo CD repository credential behavior. No dedicated PAT-backed secret is provisioned by this code right now.

If a dedicated Image Updater Git secret is adopted later, the expected annotation change is:

```yaml
argocd-image-updater.argoproj.io/write-back-method: git:secret:argocd/argocd-image-updater-git-creds
```

## PAT handling options

PAT handling is intentionally deferred. The main candidate approaches are:

1. GitHub Actions directly creates the Kubernetes Secret with `kubectl`
2. GitHub Actions passes the PAT directly inside the SSM Run Command payload
3. GitHub Actions stores the PAT in AWS Secrets Manager or SSM Parameter Store, and the SSM-managed host reads it before creating the Kubernetes Secret

Trade-offs:

1. Direct `kubectl` is simple, but depends on where cluster access exists.
2. Direct SSM payload delivery is simple operationally, but exposes the secret to a wider command payload surface.
3. Secrets Manager or Parameter Store adds one more integration step, but is the cleanest fit for the current SSM-based bootstrap model.

Recommended direction:

`Secrets Manager` or `SSM Parameter Store` is the safest and most structurally appropriate option for this project, but PAT automation is postponed for now.

## ConfigMap scope

`configmap-patch.yaml` should only contain non-secret controller-wide settings, such as:

- log level
- polling interval
- git commit user/email

It should not contain:

- PATs
- GitHub tokens
- AWS keys
- ECR passwords
- uncertain credential-specific settings

## Out of scope

This addon does not address the current KServe status issue:

- `InferenceService Ready=False`
- `Predictor ingress not created`

That remains a separate ingress/gateway problem.

## Suggested verification

```bash
kubectl kustomize public/k8s/argocd/addons/argocd-image-updater
terraform -chdir=public/terraform fmt
kubectl -n argocd get application argocd-image-updater
kubectl -n argocd get sa argocd-image-updater-controller -o yaml | grep -A5 eks.amazonaws.com/role-arn
kubectl -n argocd logs deploy/argocd-image-updater-controller --tail=300
kubectl -n inference get isvc pdm
```
