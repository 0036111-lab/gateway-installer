# Gateway Installer

Independent deployment and onboarding layer for a portable MCP gateway stack.

## Product goal

Provide a seamless path from a clean Linux server to a working, authenticated MCP gateway and supported client connection without requiring the operator to understand Docker Compose internals, OAuth metadata, reverse proxies, WireGuard, policy syntax, or client-specific quirks.

Initial client target: Hermes.

Planned core commands:

- `gateway setup`
- `gateway doctor`
- `gateway status`
- `gateway connect hermes`

The project is designed to run on generic Linux infrastructure and must not depend on any single cloud provider.

## Independence

This repository is the product repository. It must not depend at runtime on upstream GitHub repositories being available. Third-party Apache-2.0 provenance is retained only where legally required in `NOTICE` and `THIRD_PARTY_NOTICES.md`.

Customer-facing branding, CLI names, UI text, service names, examples, and default configuration should use this project's own naming and must not present upstream maintainers as the product vendor.

## Development rule

The installer should automate every step that can safely be automated. Human input should be limited to genuine decisions and approvals: infrastructure choice, owner identity, OAuth consent, business-system authorization, and security policy.
