# Gateway Installer

Independent deployment and onboarding layer for a portable MCP gateway stack.

## Product goal

Provide a seamless path from a clean Linux server to a working, authenticated MCP gateway and supported client connection without requiring the operator to understand Docker Compose internals, OAuth metadata, policy syntax, or client-specific quirks.

Initial client target: Hermes.

## MVP commands

Install this repository in editable mode on the deployment machine:

```bash
python3 -m pip install -e .
```

Then use:

```bash
gateway setup
gateway doctor
gateway status
gateway connect hermes
```

`gateway setup` copies the vendored Gateway into `/opt/gateway-platform`, generates local secrets, writes a private `.env`, creates an explicit owner-admin policy, applies a deny-domain guard, removes unsafe optional-backend fallbacks, and binds Gateway port 8000 to loopback only. Real secrets are never committed.

The Yandex OAuth client secret is requested with a hidden prompt. For non-interactive use, provide it only through the `YANDEX_OAUTH_CLIENT_SECRET` environment variable.

Use `gateway setup --start` to build and start the Docker Compose stack when Docker is already available.

`gateway doctor` validates prerequisites and known failure modes: Docker/Compose, placeholder values, owner policy, email-domain guard, effective Compose configuration, and public port exposure.

`gateway status` reports the installation, Docker Compose state, and public `/healthz` result without printing secrets.

`gateway connect hermes` prints the exact command to run on the machine where Hermes is installed. Add `--apply` only when the command is being run on that client machine.

## Current MVP boundary

The first MVP productizes Gateway configuration, safety checks, startup, health, and Hermes onboarding. Docker installation and HTTPS/reverse-proxy provisioning are the next automation layer and are intentionally not hidden behind an untested bootstrap script yet.

## Independence

This repository is the product repository. It does not depend at runtime on upstream GitHub repositories being available. The full source snapshots are stored under `vendor/gateway` and `vendor/platform`. Third-party Apache-2.0 provenance is retained only where legally required in `NOTICE` and `THIRD_PARTY_NOTICES.md`.

Customer-facing branding, CLI names, UI text, service names, examples, and default configuration use this project's own naming and do not present upstream maintainers as the product vendor.

## Development rule

The installer should automate every step that can safely be automated. Human input should be limited to genuine decisions and approvals: infrastructure choice, owner identity, OAuth consent, business-system authorization, and security policy.
