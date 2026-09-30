#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="${GATEWAY_INSTALLER_REPO:-https://github.com/0036111-lab/gateway-installer.git}"
REPO_REF="${GATEWAY_INSTALLER_REF:-main}"
REPO_DIR="${GATEWAY_INSTALLER_DIR:-/opt/gateway-installer}"

fail() {
  echo "FAIL    $*" >&2
  exit 2
}

if [[ ${EUID} -ne 0 ]]; then
  command -v sudo >/dev/null 2>&1 || fail "run as root or install sudo"
  exec sudo -E bash "$0" "$@"
fi

[[ -r /etc/os-release ]] || fail "cannot identify the operating system"
# shellcheck disable=SC1091
source /etc/os-release
case "${ID:-}" in
  ubuntu|debian) ;;
  *) fail "supported installer OS: Ubuntu/Debian; detected ${ID:-unknown}" ;;
esac

export DEBIAN_FRONTEND=noninteractive

echo "INFO    bootstrap-source     $REPO_URL"
echo "INFO    bootstrap-ref        $REPO_REF"
echo "INFO    repository-path      $REPO_DIR"

apt-get update
apt-get install -y ca-certificates curl git

if [[ -d "$REPO_DIR/.git" ]]; then
  echo "INFO    repository           updating existing checkout"
  git -C "$REPO_DIR" fetch --depth 1 origin "$REPO_REF"
  git -C "$REPO_DIR" checkout -q "$REPO_REF" || git -C "$REPO_DIR" checkout -q -B "$REPO_REF" "origin/$REPO_REF"
  git -C "$REPO_DIR" reset --hard "origin/$REPO_REF"
elif [[ -e "$REPO_DIR" ]]; then
  fail "$REPO_DIR already exists but is not a Git checkout"
else
  echo "INFO    repository           cloning public installer repository"
  git clone --depth 1 --branch "$REPO_REF" "$REPO_URL" "$REPO_DIR"
fi

exec bash "$REPO_DIR/bootstrap.sh" "$@"
