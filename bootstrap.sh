#!/usr/bin/env bash
set -Eeuo pipefail

OWNER_EMAIL=""
HOSTNAME_OVERRIDE=""
PUBLIC_IP=""
INSTALL_DIR="/opt/gateway-platform"
SKIP_CADDY=0

usage() {
  cat <<'EOF'
Usage:
  ./bootstrap.sh --owner-email EMAIL [--hostname HOST] [--public-ip IP] [--install-dir PATH] [--skip-caddy]

Purpose:
  Turn a clean Ubuntu 24.04 VM into a running Gateway test deployment.

What it automates:
  - installs Python venv support, Docker, Docker Compose, Caddy and curl
  - installs the Gateway installer CLI from this repository
  - configures the vendored Gateway with safe local secrets
  - validates the generated configuration with gateway doctor
  - builds and starts PostgreSQL, Gateway and notification worker
  - provisions HTTPS with Caddy
  - verifies the public /healthz endpoint

Defaults:
  - auth is disabled for this bootstrap smoke-test flow
  - if --hostname is omitted, the public IPv4 is detected and sslip.io is used
EOF
}

fail() {
  echo "FAIL    $*" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner-email)
      [[ $# -ge 2 ]] || fail "--owner-email requires a value"
      OWNER_EMAIL="$2"
      shift 2
      ;;
    --hostname)
      [[ $# -ge 2 ]] || fail "--hostname requires a value"
      HOSTNAME_OVERRIDE="$2"
      shift 2
      ;;
    --public-ip)
      [[ $# -ge 2 ]] || fail "--public-ip requires a value"
      PUBLIC_IP="$2"
      shift 2
      ;;
    --install-dir)
      [[ $# -ge 2 ]] || fail "--install-dir requires a value"
      INSTALL_DIR="$2"
      shift 2
      ;;
    --skip-caddy)
      SKIP_CADDY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "unknown argument: $1"
      ;;
  esac
done

[[ -n "$OWNER_EMAIL" ]] || fail "--owner-email is required"
[[ "$OWNER_EMAIL" == *"@"* ]] || fail "--owner-email must look like an email address"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ${EUID} -ne 0 ]]; then
  command -v sudo >/dev/null 2>&1 || fail "run as root or install sudo"
  exec sudo -E "$SCRIPT_DIR/bootstrap.sh" \
    --owner-email "$OWNER_EMAIL" \
    ${HOSTNAME_OVERRIDE:+--hostname "$HOSTNAME_OVERRIDE"} \
    ${PUBLIC_IP:+--public-ip "$PUBLIC_IP"} \
    --install-dir "$INSTALL_DIR" \
    $([[ $SKIP_CADDY -eq 1 ]] && printf '%s' '--skip-caddy')
fi

if [[ ! -r /etc/os-release ]]; then
  fail "cannot identify the operating system"
fi
# shellcheck disable=SC1091
source /etc/os-release
case "${ID:-}" in
  ubuntu|debian) ;;
  *) fail "supported bootstrap OS: Ubuntu/Debian; detected ${ID:-unknown}" ;;
esac

export DEBIAN_FRONTEND=noninteractive

echo "INFO    packages             installing Docker, Compose, Caddy and Python runtime"
apt-get update -y
apt-get install -y ca-certificates curl python3 python3-venv docker.io docker-compose-v2 caddy
systemctl enable --now docker >/dev/null

if [[ -z "$HOSTNAME_OVERRIDE" ]]; then
  if [[ -z "$PUBLIC_IP" ]]; then
    PUBLIC_IP="$(curl -4fsS --max-time 8 https://api.ipify.org || true)"
  fi
  [[ "$PUBLIC_IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || fail "could not detect a public IPv4; pass --public-ip or --hostname"
  HOSTNAME_OVERRIDE="${PUBLIC_IP//./-}.sslip.io"
fi

[[ "$HOSTNAME_OVERRIDE" =~ ^[A-Za-z0-9.-]+$ ]] || fail "invalid hostname: $HOSTNAME_OVERRIDE"
PUBLIC_URL="https://${HOSTNAME_OVERRIDE}"

echo "INFO    public-url           $PUBLIC_URL"

cd "$SCRIPT_DIR"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/pip install -e . >/dev/null
GATEWAY="$SCRIPT_DIR/.venv/bin/gateway"

SETUP_ARGS=(
  setup
  --auth none
  --public-url "$PUBLIC_URL"
  --owner-email "$OWNER_EMAIL"
  --install-dir "$INSTALL_DIR"
)
if [[ -d "$INSTALL_DIR" ]]; then
  SETUP_ARGS+=(--force)
fi

"$GATEWAY" "${SETUP_ARGS[@]}"
"$GATEWAY" doctor --install-dir "$INSTALL_DIR"

cd "$INSTALL_DIR"
docker compose up -d --build

if [[ $SKIP_CADDY -eq 0 ]]; then
  cat >/etc/caddy/Caddyfile <<EOF
${HOSTNAME_OVERRIDE} {
    reverse_proxy 127.0.0.1:8000
}
EOF
  caddy validate --config /etc/caddy/Caddyfile >/dev/null
  systemctl enable --now caddy >/dev/null
  systemctl reload caddy

  echo "INFO    https                waiting for public health endpoint"
  HEALTH_OK=0
  for _ in $(seq 1 20); do
    if curl -fsS --max-time 5 "${PUBLIC_URL}/healthz" >/tmp/gateway-health.json 2>/dev/null; then
      HEALTH_OK=1
      break
    fi
    sleep 3
  done
  if [[ $HEALTH_OK -ne 1 ]]; then
    fail "Gateway started locally but public HTTPS health is not ready; confirm ports 80/443 are open in the cloud firewall"
  fi
  echo "PASS    public-health        $(cat /tmp/gateway-health.json)"
fi

"$GATEWAY" status --install-dir "$INSTALL_DIR" || true

echo
printf 'PASS    bootstrap            Gateway deployment completed\n'
printf 'INFO    MCP URL              %s/mcp\n' "$PUBLIC_URL"
printf 'INFO    auth                 none (smoke-test mode; enable authentication before production use)\n'
