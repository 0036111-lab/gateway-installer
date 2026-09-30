from __future__ import annotations

import argparse
import getpass
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from .core import (
    DEFAULT_INSTALL_DIR,
    InstallerError,
    docker_ps,
    doctor_checks,
    format_checks,
    health,
    install_gateway,
    load_state,
    start_stack,
)


def _value(value: str | None, prompt: str) -> str:
    if value:
        return value.strip()
    if not sys.stdin.isatty():
        raise InstallerError(f"missing required value: {prompt}")
    entered = input(f"{prompt}: ").strip()
    if not entered:
        raise InstallerError(f"missing required value: {prompt}")
    return entered


def _secret_from_env_or_prompt(name: str, prompt: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    if not sys.stdin.isatty():
        raise InstallerError(f"set {name} in the environment for non-interactive setup")
    value = getpass.getpass(f"{prompt}: ").strip()
    if not value:
        raise InstallerError(f"missing required secret: {name}")
    return value


def cmd_setup(args: argparse.Namespace) -> int:
    public_url = _value(args.public_url, "Public HTTPS URL")
    owner_email = _value(args.owner_email, "Owner email")

    auth_mode = args.auth
    client_id = ""
    client_secret = ""
    if auth_mode == "yandex":
        client_id = _value(args.yandex_client_id, "Yandex OAuth Client ID")
        client_secret = _secret_from_env_or_prompt(
            "YANDEX_OAUTH_CLIENT_SECRET",
            "Yandex OAuth Client Secret (hidden)",
        )

    target = install_gateway(
        install_dir=args.install_dir,
        public_url=public_url,
        owner_email=owner_email,
        yandex_client_id=client_id,
        yandex_client_secret=client_secret,
        auth_enabled=auth_mode != "none",
        auth_mode=auth_mode,
        force=args.force,
        allow_http=args.allow_http,
    )
    print(f"PASS    setup                configured at {target}")
    print("PASS    secrets              generated locally; .env mode is 0600")
    print("PASS    policy               explicit owner admin + deny-domain sentinel")
    print("PASS    network              Gateway port 8000 bound to 127.0.0.1 only")
    print(f"PASS    auth                 {auth_mode}")

    if args.start:
        ok, detail = start_stack(target)
        print(f"{'PASS' if ok else 'BLOCKED':7} start                {detail}")
        return 0 if ok else 2

    print("NEXT    start                run: gateway setup --start ... or start later with Docker Compose")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    checks = doctor_checks(args.install_dir)
    print(format_checks(checks))
    return 0 if checks and all(c.status == "PASS" for c in checks) else 2


def cmd_status(args: argparse.Namespace) -> int:
    state = load_state(args.install_dir)
    if not state:
        print(f"BLOCKED installation         no installer state at {args.install_dir}")
        return 2

    print(f"PASS    installation         {state.get('install_dir', args.install_dir)}")
    print(f"INFO    owner                {state.get('owner_email', 'unknown')}")
    print(f"INFO    MCP URL              {state.get('mcp_url', 'unknown')}")
    print(f"INFO    auth                 {state.get('auth_mode', 'unknown')}")

    ok, detail = docker_ps(args.install_dir)
    print(f"{'PASS' if ok else 'BLOCKED':7} docker               {detail}")

    public_url = state.get("public_url", "")
    if public_url:
        healthy, health_detail = health(public_url)
        print(f"{'PASS' if healthy else 'BLOCKED':7} public-health        {health_detail}")
        return 0 if ok and healthy else 2
    return 2


def _hermes_command(mcp_url: str, server_name: str) -> list[str]:
    return ["hermes", "mcp", "add", server_name, "--url", mcp_url, "--auth", "oauth"]


def cmd_connect_hermes(args: argparse.Namespace) -> int:
    if args.url:
        mcp_url = args.url.rstrip("/")
        if not mcp_url.endswith("/mcp"):
            mcp_url += "/mcp"
    else:
        state = load_state(args.install_dir)
        mcp_url = state.get("mcp_url", "")
        if not mcp_url:
            raise InstallerError("MCP URL is unknown; run setup first or pass --url")

    command = _hermes_command(mcp_url, args.name)
    print("Run this on the machine where Hermes is installed:")
    print(shlex.join(command))

    if not args.apply:
        return 0
    if not shutil.which("hermes"):
        print("BLOCKED hermes               Hermes is not installed on this machine")
        return 2
    result = subprocess.run(command, text=True)
    return result.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gateway", description="Gateway productized installer")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    setup = sub.add_parser("setup", help="configure a vendored Gateway installation")
    setup.add_argument("--install-dir", type=Path, default=DEFAULT_INSTALL_DIR)
    setup.add_argument("--public-url")
    setup.add_argument("--owner-email")
    setup.add_argument(
        "--auth",
        choices=["none", "yandex"],
        default="none",
        help="authentication provider; default is none for a provider-neutral test deployment",
    )
    setup.add_argument("--yandex-client-id", help="required only when --auth yandex")
    setup.add_argument("--allow-http", action="store_true", help="allow http:// only for test environments")
    setup.add_argument("--force", action="store_true", help="backup an existing install directory before replacing it")
    setup.add_argument("--start", action="store_true", help="build and start the Docker Compose stack after setup")
    setup.set_defaults(func=cmd_setup)

    doctor = sub.add_parser("doctor", help="diagnose prerequisites, configuration and safety guards")
    doctor.add_argument("--install-dir", type=Path, default=DEFAULT_INSTALL_DIR)
    doctor.set_defaults(func=cmd_doctor)

    status = sub.add_parser("status", help="show container and public health status")
    status.add_argument("--install-dir", type=Path, default=DEFAULT_INSTALL_DIR)
    status.set_defaults(func=cmd_status)

    connect = sub.add_parser("connect", help="connect a supported MCP client")
    clients = connect.add_subparsers(dest="client", required=True)
    hermes = clients.add_parser("hermes", help="generate or apply Hermes MCP connection")
    hermes.add_argument("--install-dir", type=Path, default=DEFAULT_INSTALL_DIR)
    hermes.add_argument("--url", help="Gateway public URL or full /mcp URL")
    hermes.add_argument("--name", default="gateway")
    hermes.add_argument("--apply", action="store_true", help="execute the Hermes command on this machine")
    hermes.set_defaults(func=cmd_connect_hermes)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except InstallerError as exc:
        print(f"FAIL    {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nCANCELLED", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
