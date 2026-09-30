# Gateway Installer

Independent deployment and onboarding layer for a portable MCP gateway stack.

## Product goal

Provide a short path from a clean Linux VM to a working MCP gateway without requiring the operator to understand Docker Compose internals, secret generation, reverse-proxy configuration, TLS, or client-specific quirks.

Initial client target: Hermes.

## Stage 1 — VM already exists

The VM should already have:

- Ubuntu 24.04 or compatible Debian-based Linux
- SSH access
- a public IPv4 address
- inbound TCP 22, 80 and 443 allowed by the cloud firewall/security group
- about 2 GB RAM for comfortable Docker image builds

After the first successful SSH login, deployment is one command:

```bash
curl -fsSL https://raw.githubusercontent.com/0036111-lab/gateway-installer/main/install.sh | sudo bash -s -- --owner-email owner@example.com
```

`install.sh` installs the minimal download prerequisites, clones or refreshes this repository under `/opt/gateway-installer`, and hands off to `bootstrap.sh`.

`bootstrap.sh` then automatically:

- installs Python venv support, Docker and Docker Compose
- installs Caddy
- installs the `gateway` CLI from this repository
- detects the public IPv4 and creates an `sslip.io` hostname unless a hostname is supplied
- runs `gateway setup` with the final HTTPS URL
- generates local secrets and writes the private `.env`
- runs `gateway doctor`
- builds and starts PostgreSQL, Gateway and notification worker
- configures Caddy as the HTTPS reverse proxy
- verifies the public `/healthz` endpoint
- prints the final MCP URL

Use an existing hostname instead of `sslip.io` when needed by cloning the repository and running:

```bash
bash bootstrap.sh --owner-email owner@example.com --hostname mcp.example.com
```

The current bootstrap deliberately uses `auth none` for smoke-test deployments. Authentication is a separate product stage and must be enabled before production use.

## Stage 0 — create a Yandex Cloud VM with an LLM

For an LLM-assisted Yandex Cloud setup, use:

`docs/LLM_YANDEX_VM.md`

That runbook keeps VM provisioning separate from product deployment. It uses a normal SSH key, public IPv4, the required network ports, and then hands off immediately to the one-command installer above.

## CLI commands

For manual or advanced operation, install this repository in editable mode:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

Then use:

```bash
gateway setup
gateway doctor
gateway status
gateway connect hermes
```

`gateway setup` copies the vendored Gateway into `/opt/gateway-platform`, generates or preserves local system secrets, writes a private `.env`, creates an explicit owner-admin policy, applies a deny-domain guard, removes unsafe optional-backend fallbacks, and binds Gateway port 8000 to loopback only.

Repeated `gateway setup --force` preserves the existing PostgreSQL password, JWT secret and encryption key so an existing PostgreSQL volume is not broken by reconfiguration.

`gateway doctor` validates prerequisites and known failure modes including Docker/Compose, placeholder values, owner policy, email-domain guard, effective Compose configuration and public port exposure.

`gateway status` reports the installation, Docker Compose state and public `/healthz` result without printing secrets.

`gateway connect hermes` prints the client-side command to run where Hermes is installed.

## Independence

This repository is the product repository. It does not depend at runtime on upstream GitHub repositories being available. The full source snapshots are stored under `vendor/gateway` and `vendor/platform`. Third-party Apache-2.0 provenance is retained where legally required in `NOTICE` and `THIRD_PARTY_NOTICES.md`.

Customer-facing branding, CLI names, UI text, service names, examples and default configuration use this project's own naming and do not present upstream maintainers as the product vendor.

## Development rule

The installer should automate every step that can safely be automated. Human input should be limited to genuine decisions and approvals: infrastructure choice, owner identity, authentication/consent, business-system authorization and security policy.
