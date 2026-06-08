#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OPENSTACK_DIR="${ROOT}/private/openstack"
PATH="${ROOT}/.ha/bin:${PATH}"
export TF_IN_AUTOMATION="${TF_IN_AUTOMATION:-true}"
export TF_INPUT="${TF_INPUT:-false}"

cleanup_devstack="${HA_PRIVATE_CLOUD_CLEANUP_DEVSTACK:-false}"
require_backend_config=false

usage() {
  cat >&2 <<'EOF'
usage: ha destroy [--cleanup-devstack] [--require-backend-config]
EOF
}

log() {
  printf '[private-cloud-destroy] %s\n' "$*"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cleanup-devstack)
      cleanup_devstack="true"
      shift
      ;;
    --require-backend-config)
      require_backend_config=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      echo "unknown option: $1" >&2
      exit 64
      ;;
  esac
done

require_tool() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "required command not found: $1" >&2
    exit 1
  }
}

write_tfvars_if_present() {
  rm -f "${OPENSTACK_DIR}/backend.generated.tf" "${OPENSTACK_DIR}/backend.hcl" "${OPENSTACK_DIR}/private-cloud.auto.tfvars"
  if [[ -n "${PRIVATE_CLOUD_TFVARS:-}" ]]; then
    printf '%s' "$PRIVATE_CLOUD_TFVARS" > "${OPENSTACK_DIR}/private-cloud.auto.tfvars"
  fi
}

prepare_local_devstack_env() {
  if [[ -z "${OS_AUTH_URL:-}" ]]; then
    export OS_AUTH_URL="http://127.0.0.1:18081/identity/v3"
  fi
  export OS_USERNAME="${OS_USERNAME:-admin}"
  export OS_PASSWORD="${OS_PASSWORD:-${HA_DEVSTACK_PASSWORD:-hybrid-ai-devstack}}"
  export OS_PROJECT_NAME="${OS_PROJECT_NAME:-admin}"
  export OS_USER_DOMAIN_NAME="${OS_USER_DOMAIN_NAME:-Default}"
  export OS_PROJECT_DOMAIN_NAME="${OS_PROJECT_DOMAIN_NAME:-Default}"
  export OS_REGION_NAME="${OS_REGION_NAME:-RegionOne}"
  export OS_IDENTITY_API_VERSION="${OS_IDENTITY_API_VERSION:-3}"
}

prepare_ssh_public_key() {
  if [[ -n "${TF_VAR_ssh_public_key:-}" ]]; then
    return
  fi
  if [[ -n "${PRIVATE_CLOUD_SSH_PUBLIC_KEY:-}" ]]; then
    export TF_VAR_ssh_public_key="$PRIVATE_CLOUD_SSH_PUBLIC_KEY"
    return
  fi
  local key="${ROOT}/.ha/ssh/hybrid-ai-private-admin"
  if [[ -f "${key}.pub" ]]; then
    export TF_VAR_ssh_public_key
    TF_VAR_ssh_public_key="$(cat "${key}.pub")"
    return
  fi
  install -d -m 0700 "${ROOT}/.ha/ssh"
  ssh-keygen -t ed25519 -N '' -f "$key" >/dev/null
  export TF_VAR_ssh_public_key
  TF_VAR_ssh_public_key="$(cat "${key}.pub")"
}

local_backend_state_path() {
  local backend_hcl="$1"

  [[ "${TF_BACKEND_TYPE:-local}" == "local" ]] || return 1
  awk '
    /^[[:space:]]*path[[:space:]]*=/ {
      sub(/^[^=]*=/, "", $0)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0)
      gsub(/^"|"$/, "", $0)
      print $0
      exit
    }
  ' "$backend_hcl"
}

prepare_noninteractive_backend_init() {
  local module_dir="$1"
  local backend_hcl="$2"
  local backend_path
  local archive_dir

  backend_path="$(local_backend_state_path "$backend_hcl" || true)"
  [[ -n "$backend_path" ]] || return 1
  if [[ "$backend_path" != /* ]]; then
    backend_path="${module_dir}/${backend_path}"
  fi

  mkdir -p "$(dirname "$backend_path")"
  rm -f "${module_dir}/.terraform/terraform.tfstate"

  if [[ -s "$backend_path" ]]; then
    if [[ -s "${module_dir}/terraform.tfstate" ]]; then
      archive_dir="${ROOT}/.ha/openstack/state-archive/$(date -u +%Y%m%dT%H%M%SZ)"
      mkdir -p "$archive_dir"
      mv "${module_dir}/terraform.tfstate" "${archive_dir}/terraform.tfstate"
      log "archived stale root Terraform state before backend reconfigure: ${archive_dir}/terraform.tfstate"
    fi
    return 0
  fi

  return 1
}

terraform_init() {
  local backend_config="${TF_BACKEND_CONFIG:-}"
  local backend_config_compact="${backend_config//[[:space:]]/}"

  if [[ "$require_backend_config" == "true" && -z "$backend_config_compact" ]]; then
    echo "TF_BACKEND_CONFIG is required when --require-backend-config is set" >&2
    exit 1
  fi

  if [[ -n "$backend_config_compact" ]]; then
    printf 'terraform {\n  backend "%s" {}\n}\n' "${TF_BACKEND_TYPE:-local}" > "${OPENSTACK_DIR}/backend.generated.tf"
    printf '%s' "$backend_config" > "${OPENSTACK_DIR}/backend.hcl"
    if prepare_noninteractive_backend_init "$OPENSTACK_DIR" "${OPENSTACK_DIR}/backend.hcl"; then
      terraform -chdir="$OPENSTACK_DIR" init -input=false -reconfigure -backend-config=backend.hcl
    else
      terraform -chdir="$OPENSTACK_DIR" init -input=false -migrate-state -force-copy -backend-config=backend.hcl
    fi
  else
    rm -f "${OPENSTACK_DIR}/.terraform/terraform.tfstate"
    terraform -chdir="$OPENSTACK_DIR" init -input=false -reconfigure
  fi
}

cleanup_kubernetes_best_effort() {
  local kubeconfig="${ROOT}/.ha/openstack/kubeconfig"

  command -v kubectl >/dev/null 2>&1 || return 0
  [[ -f "$kubeconfig" ]] || return 0
  export KUBECONFIG="$kubeconfig"
  if ! kubectl --request-timeout=20s get nodes >/dev/null 2>&1; then
    log "Kubernetes API is not reachable; skipping Kubernetes cleanup"
    return 0
  fi

  log "cleaning Kubernetes workloads before Terraform destroy"
  kubectl delete jobs --all --all-namespaces --ignore-not-found=true --timeout=60s || true
  kubectl delete deployments --all --all-namespaces --ignore-not-found=true --timeout=120s || true
  kubectl delete statefulsets --all --all-namespaces --ignore-not-found=true --timeout=120s || true
  kubectl delete daemonsets --all --all-namespaces --ignore-not-found=true --timeout=120s || true
  kubectl delete pvc --all --all-namespaces --ignore-not-found=true --timeout=120s || true
  kubectl delete pv --all --ignore-not-found=true --timeout=120s || true
}

main() {
  require_tool terraform
  prepare_local_devstack_env
  prepare_ssh_public_key
  write_tfvars_if_present
  cleanup_kubernetes_best_effort

  log "terraform init"
  terraform_init

  log "terraform destroy"
  terraform -chdir="$OPENSTACK_DIR" destroy -input=false -auto-approve

  if [[ "$cleanup_devstack" == "true" ]]; then
    require_tool lxc
    log "removing ha-openstack LXD container"
    lxc stop ha-openstack --force 2>/dev/null || true
    lxc delete ha-openstack --force 2>/dev/null || true
  fi

  rm -f "${OPENSTACK_DIR}/backend.generated.tf" "${OPENSTACK_DIR}/backend.hcl" "${OPENSTACK_DIR}/private-cloud.auto.tfvars"
  log "complete"
}

main "$@"
