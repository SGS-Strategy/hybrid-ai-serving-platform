#!/usr/bin/env bash
# GPU vfio 자동 바인딩 + OpenStack VM 기동 (kt-cloud 호스트, 부팅 시 root 실행).
#
# 문제: kolla 경로엔 GPU vfio 자동바인딩이 없다. 호스트를 리부트하면
#   0000:08:00.0(RTX GPU) + 0000:08:00.1(HDMI audio)가 nvidia/snd_hda_intel 로 잡혀
#   nova 가 GPU passthrough VM 을 기동하지 못한다(rc=0 인데 SHUTOFF 롤백).
# 또한 resume_guests_state_on_host_boot=false 라 리부트 후 모든 VM 이 SHUTOFF 로 남는다.
#
# 이 스크립트는:
#   1) GPU + audio 함수를 vfio-pci 로 (재)바인딩 (이미 vfio면 no-op)
#   2) SHUTOFF 인 OpenStack VM 을 전부 기동 (GPU VM 은 1) 이후라야 ACTIVE 로 뜬다)
# systemd(gpu-vfio-autobind.service)로 부팅 때 1회 실행하고, 수동 재적용도 가능하다.
set -uo pipefail

GPU_FUNCS=("0000:08:00.0" "0000:08:00.1")
# 이 카드 고유 ID (vendor:device) — 안전장치로 함수가 실제 이 GPU 인지 확인.
EXPECT_VENDOR="0x10de"
OPENRC="/etc/kolla/admin-openrc.sh"
OS_BIN="/home/kt/.ha/kolla-venv/bin/openstack"

log() { printf '[gpu-vfio] %s\n' "$*"; }

bind_one_vfio() {
  local d="$1" cur
  [[ -e "/sys/bus/pci/devices/$d" ]] || { log "$d 없음 — skip"; return 0; }
  local ven; ven="$(cat "/sys/bus/pci/devices/$d/vendor" 2>/dev/null)"
  [[ "$ven" == "$EXPECT_VENDOR" ]] || { log "$d vendor=$ven (expected $EXPECT_VENDOR) — 안전상 skip"; return 0; }
  cur="$(basename "$(readlink "/sys/bus/pci/devices/$d/driver" 2>/dev/null)" 2>/dev/null)"
  if [[ "$cur" == "vfio-pci" ]]; then
    log "$d 이미 vfio-pci — ok"; return 0
  fi
  log "$d 현재 드라이버=${cur:-none} → vfio-pci 로 재바인딩"
  echo "vfio-pci" > "/sys/bus/pci/devices/$d/driver_override" 2>/dev/null
  [[ -n "$cur" ]] && echo "$d" > "/sys/bus/pci/devices/$d/driver/unbind" 2>/dev/null
  echo "$d" > /sys/bus/pci/drivers_probe 2>/dev/null
  cur="$(basename "$(readlink "/sys/bus/pci/devices/$d/driver" 2>/dev/null)" 2>/dev/null)"
  [[ "$cur" == "vfio-pci" ]] && log "$d → vfio-pci 완료" || log "$d 재바인딩 실패(드라이버=$cur)"
}

start_shutoff_vms() {
  [[ -f "$OPENRC" && -x "$OS_BIN" ]] || { log "openstack CLI/openrc 없음 — VM 기동 skip"; return 0; }
  # shellcheck disable=SC1090
  source "$OPENRC"
  local vms
  vms="$("$OS_BIN" server list --all-projects --status SHUTOFF -c Name -f value 2>/dev/null)"
  if [[ -z "$vms" ]]; then log "SHUTOFF VM 없음 — 기동 skip"; return 0; fi
  while IFS= read -r vm; do
    [[ -z "$vm" ]] && continue
    log "server start: $vm"
    "$OS_BIN" server start "$vm" >/dev/null 2>&1 || log "  $vm 기동 요청 실패"
  done <<< "$vms"
}

main() {
  [[ "$(id -u)" -eq 0 ]] || { echo "root 필요(sudo)" >&2; exit 1; }
  modprobe vfio-pci 2>/dev/null || true
  for d in "${GPU_FUNCS[@]}"; do bind_one_vfio "$d"; done
  # nova-compute(kolla 컨테이너)가 안정된 뒤 VM 을 올린다.
  case "${1:-}" in
    --no-vm) log "VM 기동 생략(--no-vm)";;
    *) start_shutoff_vms;;
  esac
  log "완료"
}
main "$@"
