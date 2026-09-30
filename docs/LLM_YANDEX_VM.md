# LLM runbook: Yandex Cloud VM → Gateway bootstrap

Purpose: guide a human through creating a clean Yandex Cloud VM, then hand off immediately to the repository's one-command installer. The LLM should minimize user actions and avoid alternative access schemes unless the chosen path is proven blocked.

## Operating rules for the LLM

- Use one primary route from start to finish.
- Give one next action at a time.
- Always say where the action is performed: Yandex Cloud UI or the user's local terminal.
- Do not use OS Login for this runbook. Use a normal SSH key pair.
- Do not ask the user to paste private keys, OAuth secrets, tokens, or passwords into chat.
- Do not repeat checks that are already proven.
- If the same step fails twice, stop repeating it and diagnose the exact layer before changing architecture.
- Do not touch any existing production VM while preparing the new VM.

## Stage A — create the VM in Yandex Cloud

Create a new Linux VM in Yandex Cloud Compute Cloud with these baseline settings:

- OS: Ubuntu 24.04 LTS
- CPU: 1–2 vCPU
- RAM: 2 GB minimum for comfortable Docker image builds
- Disk: 20 GB or more
- Public IPv4: enabled
- OS Login: disabled
- Access: existing public SSH key or a newly generated dedicated SSH key

Use a custom security group for the public VM when possible:

- inbound TCP 22 from the operator's trusted source IP/range
- inbound TCP 80 from `0.0.0.0/0`
- inbound TCP 443 from `0.0.0.0/0`
- outbound traffic allowed as required for package downloads, GitHub, TLS issuance, and container images

Record the exact SSH username chosen in the VM form and the VM's public IPv4 address.

Yandex Cloud requires the public half of the SSH key on the VM and the private half to remain with the user. A VM with a public IP also needs the relevant cloud permission and a security group permitting SSH traffic.

## Stage B — verify one SSH login

On the user's local macOS/Linux terminal, connect with the matching private key:

```bash
ssh -i ~/.ssh/<private-key-file> <username>@<public-ip>
```

If the host fingerprint prompt appears, verify/accept it once. When the shell prompt on the VM appears, SSH is proven and the Yandex-specific stage is complete.

Do not continue changing Yandex access settings after successful SSH login.

## Stage C — hand off to the repository installer

Once inside the VM, run the public installer entrypoint:

```bash
curl -fsSL https://raw.githubusercontent.com/0036111-lab/gateway-installer/main/install.sh | sudo bash -s -- --owner-email <owner-email>
```

This command is the boundary between cloud provisioning and product deployment.

The installer will obtain the repository and hand off to `bootstrap.sh`, which installs the required host packages, Docker, Docker Compose and Caddy; installs the `gateway` CLI; detects the public IP; creates an `sslip.io` hostname by default; configures the Gateway; runs `gateway doctor`; builds and starts PostgreSQL, Gateway and the notification worker; configures HTTPS; verifies `/healthz`; and prints the MCP URL.

## Success criteria

The deployment is complete when the installer prints a successful bootstrap result and the public health endpoint returns JSON containing:

```json
{"ok": true}
```

The resulting MCP endpoint has the form:

```text
https://<host>/mcp
```

## Important boundary

VM creation is an infrastructure step. Everything after the first successful SSH login should be handled by this repository's installer rather than by a long sequence of manual shell commands.

Authentication is intentionally separate from this smoke-test bootstrap. The current default bootstrap uses `auth none`; production authentication must be configured as a later stage.
