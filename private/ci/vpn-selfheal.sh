#!/usr/bin/env bash
# ECR-over-VPN 셀프힐 (kt-cloud 호스트, user=kt 로 주기 실행).
#
# 재배포/리부트/터널드롭으로 ECR-over-VPN 이 깨지는 4가지 유형을 자동 감지·복구한다:
#   (1) resolver inbound IP drift   → AWS 조회 후 CoreDNS amazonaws 포워딩 재패치 (호스트 단독, 안전)
#   (2) 터널 SA 다운(엔드포인트 동일) → ssh MacMini 로 ipsec down/up 재수립
#   (3) AWS 재배포로 터널 엔드포인트/PSK 변경 → gh 로 VPN Connect 워크플로 트리거(bastion 재프로비전)
#   (4) 호스트 데이터플레인(kolla-egress-nat) 비활성 / 충돌 dataplane 타이머 부활 → 재적용/무력화
#
# PSK 는 terraform output 에만 있으므로 (3) 만 GitHub Actions 를 경유한다. 나머지는 호스트 단독.
#
# 사용:
#   ./vpn-selfheal.sh --check          # 진단만(read-only) 출력
#   ./vpn-selfheal.sh --heal           # 감지+복구 (systemd 타이머가 호출)
#   VPN_SELFHEAL_ALLOW_GH=1 ./vpn-selfheal.sh --heal   # (3) gh 트리거 허용
set -uo pipefail
export AWS_REGION="${AWS_REGION:-ap-northeast-2}"
export PATH="/home/kt/project/hybrid-ai-serving-platform/.ha/bin:/home/kt/.ha/kolla-venv/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
export KUBECONFIG="${KUBECONFIG:-/home/kt/project/hybrid-ai-serving-platform/.ha/openstack/kubeconfig}"

REPO_DIR="/home/kt/project/hybrid-ai-serving-platform"
COREDNS_WIRE="$REPO_DIR/private/ci/ecr-vpn-coredns.sh"
LOCAL_CIDR="10.42.0.0/24"
BASTION_SSH="MacMini"
BASTION_IPSEC_CONF="/opt/homebrew/etc/ipsec.conf"
BASTION_IPSEC_BIN="/opt/homebrew/bin/ipsec"
ALLOW_GH="${VPN_SELFHEAL_ALLOW_GH:-0}"
GH_COOLDOWN_FILE="/tmp/.vpn-selfheal-gh-last"
GH_COOLDOWN_SEC=1200
MODE="${1:---heal}"

log() { printf '[vpn-selfheal] %s %s\n' "$(date -u +%H:%M:%S)" "$*"; }

aws_q() { aws --region "$AWS_REGION" "$@" 2>/dev/null; }

# AWS 도달/자격증명 확인 (mid-churn/down 시 아무것도 안 하려고 게이트로 사용)
aws_reachable() { aws_q sts get-caller-identity --query Account --output text | grep -qE '^[0-9]+$'; }

# 현재 AWS resolver INBOUND endpoint 사설 IP (공백 구분, 정렬, 중복제거)
current_resolver_ips() {
  aws_q ec2 describe-network-interfaces \
    --filters "Name=description,Values=*Resolver*" \
    --query 'NetworkInterfaces[?contains(Description, `rslvr-in`)].PrivateIpAddress' --output text \
    | tr '\t' '\n' | grep -E '^[0-9]' | sort -u | tr '\n' ' ' | sed 's/ *$//'
}

# 두 번 조회해 동일할 때만 신뢰(전환 중 부분결과 방지). 불안정하면 빈 문자열.
stable_resolver_ips() {
  local a b; a="$(current_resolver_ips)"; sleep 2; b="$(current_resolver_ips)"
  [[ -n "$a" && "$a" == "$b" ]] && printf '%s' "$a" || printf ''
}

# CoreDNS Corefile 의 amazonaws forward IP (정렬)
coredns_ips() {
  kubectl -n kube-system get cm coredns -o jsonpath='{.data.Corefile}' 2>/dev/null \
    | awk '/amazonaws/{f=1} f&&/forward/{for(i=3;i<=NF;i++)if($i ~ /^[0-9]/)print $i}' | sort -u | tr '\n' ' ' | sed 's/ *$//'
}

# 10.42.0.0/24 라우트를 가진 available VPN 의 UP 터널 outside IP (server-side filter)
current_tunnel_ip() {
  aws_q ec2 describe-vpn-connections \
    --filters "Name=state,Values=available" "Name=route.destination-cidr-block,Values=${LOCAL_CIDR}" \
    --query "VpnConnections[].VgwTelemetry[?Status=='UP'].OutsideIpAddress" --output text | awk 'NF{print $1; exit}'
}

bastion_right() { ssh -o BatchMode=yes -o ConnectTimeout=8 "$BASTION_SSH" "grep -m1 -oE 'right=[0-9.]+' $BASTION_IPSEC_CONF 2>/dev/null | cut -d= -f2" 2>/dev/null; }
bastion_sa_up() { ssh -o BatchMode=yes -o ConnectTimeout=8 "$BASTION_SSH" "sudo -n $BASTION_IPSEC_BIN status 2>/dev/null | grep -c '1 up'" 2>/dev/null; }

heal_coredns() {
  local want="$1"
  log "CoreDNS 재패치 → $want"
  # shellcheck disable=SC2086
  KUBECONFIG="$KUBECONFIG" "$COREDNS_WIRE" $want >/dev/null 2>&1 && log "CoreDNS ok" || log "CoreDNS 재패치 실패"
}

heal_tunnel_reup() {
  log "bastion 터널 재수립(ipsec down/up)"
  ssh -o BatchMode=yes -o ConnectTimeout=8 "$BASTION_SSH" \
    "sudo -n $BASTION_IPSEC_BIN down aws-tunnel1 >/dev/null 2>&1; sudo -n $BASTION_IPSEC_BIN up aws-tunnel1 >/dev/null 2>&1 &" 2>/dev/null
  sleep 8
  [[ "$(bastion_sa_up)" == "1" ]] && log "터널 UP" || log "터널 아직 미수립(재시도 대기)"
}

trigger_gh_rewire() {
  [[ "$ALLOW_GH" == "1" ]] || { log "AWS 재배포 감지(엔드포인트 변경) — gh 트리거는 VPN_SELFHEAL_ALLOW_GH=1 필요. 수동: gh workflow run vpn-connect.yml"; return 0; }
  local now last; now=$(date +%s); last=$(cat "$GH_COOLDOWN_FILE" 2>/dev/null || echo 0)
  if (( now - last < GH_COOLDOWN_SEC )); then log "gh 트리거 쿨다운 중(최근 실행)"; return 0; fi
  log "VPN Connect 워크플로 트리거(bastion 재프로비전+CoreDNS)"
  gh workflow run "VPN Connect (ECR-over-VPN)" --repo "$(cd "$REPO_DIR" && gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)" \
     -f bring_up_tunnel=true -f wire_coredns=true -f wire_dataplane=false >/dev/null 2>&1 \
     && { echo "$now" > "$GH_COOLDOWN_FILE"; log "gh 트리거 완료"; } || log "gh 트리거 실패"
}

ensure_dataplane() {
  # 정식 호스트 설정(route+SNAT→10.42.0.254)은 kolla-egress-nat.service. 활성 보장.
  systemctl is-active --quiet kolla-egress-nat.service || { log "kolla-egress-nat 재적용"; sudo -n systemctl start kolla-egress-nat.service 2>/dev/null; }
  # 충돌하는 ecr-vpn-dataplane 타이머(qrouter no-SNAT)가 살아있으면 무력화.
  if systemctl is-enabled --quiet ecr-vpn-dataplane.timer 2>/dev/null; then
    log "충돌 타이머 ecr-vpn-dataplane 비활성화"; sudo -n systemctl disable --now ecr-vpn-dataplane.timer 2>/dev/null
  fi
}

main() {
  local rip cip tip bright saup
  cip="$(coredns_ips)"; bright="$(bastion_right)"

  # AWS 미도달(자격증명/네트워크) 시엔 AWS 기반 판단을 하지 않는다.
  if ! aws_reachable; then
    log "AWS 미도달 — dataplane/터널 로컬 점검만 수행(재배포 판단 skip)"
    [[ "$MODE" == "--check" ]] && return 0
    ensure_dataplane
    saup="$(bastion_sa_up)"; [[ "$saup" != "1" && -n "$bright" ]] && { log "SA 다운 → 재수립"; heal_tunnel_reup; }
    return 0
  fi

  rip="$(stable_resolver_ips)"; tip="$(current_tunnel_ip)"
  log "resolver(AWS,stable)=[$rip] coredns=[$cip] tunnel_up(AWS)=[$tip] bastion_right=[$bright]"

  if [[ "$MODE" == "--check" ]]; then
    saup="$(bastion_sa_up)"; log "bastion SA up=[$saup]"
    [[ -n "$rip" && "$rip" != "$cip" ]] && log "DRIFT: CoreDNS resolver IP 불일치"
    [[ -n "$tip" && -n "$bright" && "$tip" != "$bright" ]] && log "DRIFT: 터널 엔드포인트 변경(재배포)"
    [[ -z "$tip" ]] && log "주의: 활성 터널(10.42 route, UP) 없음 — AWS teardown/전환 중일 수 있어 재배포 트리거 보류"
    return 0
  fi

  ensure_dataplane

  # AWS 가 도달하지만 활성 터널이 아예 없으면(teardown/전환 중) 파괴적 조치 보류.
  if [[ -z "$tip" ]]; then
    log "활성 터널 없음 — AWS 전환/teardown 판단, 복구 보류(다음 주기 재평가)"
    return 0
  fi

  # (3) 엔드포인트 변경(재배포) — PSK 재키 필요 → gh. (동시에 resolver 도 바뀌었을 것이므로 여기서 종료)
  if [[ -n "$tip" && -n "$bright" && "$tip" != "$bright" ]]; then
    log "터널 엔드포인트 변경 감지: AWS=$tip bastion=$bright (AWS 재배포)"
    trigger_gh_rewire
    return 0
  fi

  # (1) resolver drift → CoreDNS 재패치 (호스트 단독)
  if [[ -n "$rip" && "$rip" != "$cip" ]]; then
    heal_coredns "$rip"
  fi

  # (2) 엔드포인트 동일한데 SA 다운 → 재수립
  saup="$(bastion_sa_up)"
  if [[ "$saup" != "1" ]]; then
    log "SA 다운(엔드포인트 동일) → 재수립"
    heal_tunnel_reup
  fi

  log "완료"
}
main
