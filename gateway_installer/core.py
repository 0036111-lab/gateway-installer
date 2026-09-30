from __future__ import annotations

import json
import os
import secrets
import shutil
import stat
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
VENDORED_GATEWAY = REPO_ROOT / "vendor" / "gateway"
DEFAULT_INSTALL_DIR = Path(os.environ.get("GATEWAY_INSTALL_DIR", "/opt/gateway-platform"))
STATE_FILE = ".gateway-installer-state.json"


class InstallerError(RuntimeError):
    pass


@dataclass
class Check:
    name: str
    status: str
    detail: str


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=check,
    )


def normalize_public_url(value: str, *, allow_http: bool = False) -> str:
    value = value.strip().rstrip("/")
    if not value:
        raise InstallerError("public URL is required")
    if value.startswith("https://"):
        return value
    if allow_http and value.startswith("http://"):
        return value
    raise InstallerError("public URL must use https:// (or pass --allow-http for a test environment)")


def _write_private(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def _env_lines(
    public_url: str,
    client_id: str = "",
    client_secret: str = "",
    *,
    auth_enabled: bool = False,
    preserved: dict[str, str] | None = None,
) -> str:
    preserved = preserved or {}
    postgres_password = preserved.get("POSTGRES_PASSWORD") or secrets.token_urlsafe(32)
    jwt_secret = preserved.get("GATEWAY_JWT_SECRET") or secrets.token_urlsafe(48)
    encryption_key = preserved.get("GATEWAY_USER_TOKEN_ENCRYPTION_KEY") or secrets.token_urlsafe(32)
    values = {
        "POSTGRES_PASSWORD": postgres_password,
        "GATEWAY_JWT_SECRET": jwt_secret,
        "GATEWAY_USER_TOKEN_ENCRYPTION_KEY": encryption_key,
        "GATEWAY_AUTH_ENABLED": "true" if auth_enabled else "false",
        "GATEWAY_PUBLIC_URL": public_url,
        "GATEWAY_ISSUER_URL": public_url,
        "GATEWAY_RESOURCE_URL": f"{public_url}/mcp",
        "GATEWAY_ALLOWED_EMAIL_DOMAINS": "gateway.invalid",
        "GATEWAY_RESOURCE_POLICY_MODE": "permissive",
        "YANDEX_OAUTH_CLIENT_ID": client_id.strip(),
        "YANDEX_OAUTH_CLIENT_SECRET": client_secret.strip(),
        "YANDEX_OAUTH_SCOPES": "login:email login:info" if auth_enabled and client_id.strip() else "",
        "YONOTE_BASE_URL": "",
        "GITLAB_API_BASE_URL": "",
    }
    return "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"


def _patch_policy(path: Path, owner_email: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    owner = owner_email.strip().lower()
    if "@" not in owner:
        raise InstallerError("owner identity must be an email address")
    data["allowed_email_domains"] = ["gateway.invalid"]
    users = data.setdefault("users", {})
    users[owner] = {"groups": ["admins"]}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _harden_compose(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    replacements = {
        '      - "${GATEWAY_PORT:-8000}:8000"': '      - "127.0.0.1:${GATEWAY_PORT:-8000}:8000"',
        "GATEWAY_ALLOWED_EMAIL_DOMAINS: ${GATEWAY_ALLOWED_EMAIL_DOMAINS:-}": "GATEWAY_ALLOWED_EMAIL_DOMAINS: ${GATEWAY_ALLOWED_EMAIL_DOMAINS:-gateway.invalid}",
        "YONOTE_BASE_URL: ${YONOTE_BASE_URL:-https://wiki.example.com}": "YONOTE_BASE_URL: ${YONOTE_BASE_URL-}",
        "GITLAB_API_BASE_URL: ${GITLAB_API_BASE_URL:-https://gitlab.example.com/api/v4}": "GITLAB_API_BASE_URL: ${GITLAB_API_BASE_URL-}",
        "YANDEX_OAUTH_CLIENT_ID: ${YANDEX_OAUTH_CLIENT_ID:?set YANDEX_OAUTH_CLIENT_ID}": "YANDEX_OAUTH_CLIENT_ID: ${YANDEX_OAUTH_CLIENT_ID:-}",
        "YANDEX_OAUTH_CLIENT_SECRET: ${YANDEX_OAUTH_CLIENT_SECRET:?set YANDEX_OAUTH_CLIENT_SECRET}": "YANDEX_OAUTH_CLIENT_SECRET: ${YANDEX_OAUTH_CLIENT_SECRET:-}",
    }
    for old, new in replacements.items():
        if old not in text:
            raise InstallerError(f"expected compose pattern not found: {old}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def install_gateway(
    *,
    install_dir: Path,
    public_url: str,
    owner_email: str,
    yandex_client_id: str = "",
    yandex_client_secret: str = "",
    auth_enabled: bool = False,
    auth_mode: str = "none",
    force: bool = False,
    allow_http: bool = False,
) -> Path:
    public_url = normalize_public_url(public_url, allow_http=allow_http)
    if not VENDORED_GATEWAY.exists():
        raise InstallerError(f"vendored gateway source not found at {VENDORED_GATEWAY}")

    install_dir = install_dir.expanduser().resolve()
    preserved_env: dict[str, str] = {}
    if install_dir.exists():
        if not force:
            raise InstallerError(f"install directory already exists: {install_dir}; use --force to back it up first")
        preserved_env = parse_env(install_dir / ".env")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = install_dir.with_name(f"{install_dir.name}.backup-{stamp}")
        install_dir.rename(backup)

    install_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(VENDORED_GATEWAY, install_dir)

    _patch_policy(install_dir / "gateway-policy.json", owner_email)
    _harden_compose(install_dir / "docker-compose.yml")
    _write_private(
        install_dir / ".env",
        _env_lines(
            public_url,
            yandex_client_id,
            yandex_client_secret,
            auth_enabled=auth_enabled,
            preserved=preserved_env,
        ),
    )

    state = {
        "schema": 1,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "install_dir": str(install_dir),
        "public_url": public_url,
        "owner_email": owner_email.strip().lower(),
        "auth_mode": auth_mode,
        "mcp_url": f"{public_url}/mcp",
    }
    (install_dir / STATE_FILE).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return install_dir


def load_state(install_dir: Path) -> dict:
    path = install_dir / STATE_FILE
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def doctor_checks(install_dir: Path) -> list[Check]:
    checks: list[Check] = []

    checks.append(Check("vendored-source", "PASS" if VENDORED_GATEWAY.exists() else "FAIL", str(VENDORED_GATEWAY)))
    checks.append(Check("docker", "PASS" if shutil.which("docker") else "BLOCKED", "docker binary present" if shutil.which("docker") else "Docker is not installed"))

    if shutil.which("docker"):
        result = run(["docker", "compose", "version"], check=False)
        checks.append(Check("docker-compose", "PASS" if result.returncode == 0 else "FAIL", (result.stdout or result.stderr).strip()))

    if not install_dir.exists():
        checks.append(Check("installation", "BLOCKED", f"not installed at {install_dir}"))
        return checks

    env = parse_env(install_dir / ".env")
    checks.append(Check("env-file", "PASS" if env else "FAIL", str(install_dir / ".env")))

    risky: list[str] = []
    for key, value in env.items():
        low = value.lower()
        if "change-me" in low or "example.com" in low or "example.org" in low:
            risky.append(key)
    checks.append(Check("placeholders", "PASS" if not risky else "FAIL", "none" if not risky else ", ".join(risky)))

    allowed = env.get("GATEWAY_ALLOWED_EMAIL_DOMAINS", "")
    checks.append(Check("email-domain-guard", "PASS" if allowed else "FAIL", allowed or "empty allow-list can become allow-all"))

    compose = install_dir / "docker-compose.yml"
    text = compose.read_text(encoding="utf-8") if compose.exists() else ""
    public_bind = '"${GATEWAY_PORT:-8000}:8000"' in text and '"127.0.0.1:${GATEWAY_PORT:-8000}:8000"' not in text
    checks.append(Check("gateway-bind", "PASS" if not public_bind else "FAIL", "loopback-only" if not public_bind else "port 8000 is published on all interfaces"))

    policy = install_dir / "gateway-policy.json"
    if policy.exists():
        data = json.loads(policy.read_text(encoding="utf-8"))
        checks.append(Check("owner-policy", "PASS" if data.get("users") else "FAIL", f"{len(data.get('users', {}))} explicit user(s)"))
    else:
        checks.append(Check("owner-policy", "FAIL", "gateway-policy.json missing"))

    if shutil.which("docker") and (install_dir / ".env").exists():
        result = run(["docker", "compose", "config", "--quiet"], cwd=install_dir, check=False)
        checks.append(Check("compose-config", "PASS" if result.returncode == 0 else "FAIL", (result.stderr or "valid").strip()))

    return checks


def health(public_url: str, timeout: float = 5.0) -> tuple[bool, str]:
    url = public_url.rstrip("/") + "/healthz"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            data = json.loads(body)
            return bool(data.get("ok")), body
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return False, str(exc)


def docker_ps(install_dir: Path) -> tuple[bool, str]:
    if not shutil.which("docker"):
        return False, "Docker is not installed"
    result = run(["docker", "compose", "ps"], cwd=install_dir, check=False)
    return result.returncode == 0, (result.stdout or result.stderr).strip()


def start_stack(install_dir: Path) -> tuple[bool, str]:
    if not shutil.which("docker"):
        return False, "Docker is not installed"
    result = run(["docker", "compose", "up", "-d", "--build"], cwd=install_dir, check=False)
    return result.returncode == 0, (result.stdout or result.stderr).strip()


def format_checks(checks: Iterable[Check]) -> str:
    rows = [f"{c.status:7} {c.name:20} {c.detail}" for c in checks]
    return "\n".join(rows)
