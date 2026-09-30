# LLM runbook: Yandex Cloud VM → Gateway bootstrap

Purpose: guide a human from an initial environment check through creation of a Yandex Cloud VM and all the way to a ready MCP endpoint. The LLM should minimize user actions, use one primary route, and make progress visible after every completed action.

## Mandatory operating rules for the LLM

- Use one primary route from start to finish.
- Give one next action at a time.
- Always say where the action is performed: Yandex Cloud UI, the user's local terminal, or the VM terminal.
- Do not use OS Login for this runbook. Use a normal SSH key pair.
- Do not ask the user to paste private keys, OAuth secrets, tokens, or passwords into chat.
- Do not repeat checks that are already proven.
- If the same step fails twice, stop repeating it and diagnose the exact layer before changing architecture.
- Do not touch an existing production VM while preparing a new VM.
- Do not change a working Gateway configuration during diagnosis.
- After EVERY completed action, immediately show the full progress map before giving the next action.
- A completed action must be marked `✅`. The current action must be marked `▶️`. Future actions must be marked `⬜`.
- The progress map must always show the complete route to the final MCP URL, not only the current stage.

## Mandatory progress map

After every completed action, show this block with current statuses updated:

```text
ПРОГРЕСС РАЗВЁРТЫВАНИЯ

⬜ 1. Диагностика целевой среды
⬜ 2. Создание VM в Yandex Cloud
⬜ 3. Проверка SSH-доступа
⬜ 4. Запуск installer
⬜ 5. Docker / Docker Compose / Caddy
⬜ 6. Gateway + PostgreSQL + worker
⬜ 7. HTTPS / sslip.io
⬜ 8. Healthcheck
⬜ 9. Готовый MCP URL

Сейчас: <текущее действие>
Следующий шаг: <одно следующее действие>
```

Example after VM creation is finished:

```text
ПРОГРЕСС РАЗВЁРТЫВАНИЯ

✅ 1. Диагностика целевой среды
✅ 2. Создание VM в Yandex Cloud
▶️ 3. Проверка SSH-доступа
⬜ 4. Запуск installer
⬜ 5. Docker / Docker Compose / Caddy
⬜ 6. Gateway + PostgreSQL + worker
⬜ 7. HTTPS / sslip.io
⬜ 8. Healthcheck
⬜ 9. Готовый MCP URL

Сейчас: проверяем первый вход по SSH.
Следующий шаг: выполнить одну SSH-команду в локальном терминале.
```

Do not display the progress block before an action has actually been completed unless it is the initial map shown at the start of the run.

## Stage 1 — diagnose the target environment

Before making any changes, establish what environment the user is working with.

Check only what is needed to choose the safe route:

- Is this a new/clean VM or an existing server?
- Does Gateway already exist?
- Are Docker / Docker Compose / Caddy already installed?
- Does `/opt/gateway-platform` already exist?
- If Gateway exists, is authentication already configured?
- Is there an existing hostname and Caddy configuration?
- Is the existing Gateway healthy?

During diagnosis, do not modify anything.

At the end of diagnosis, explicitly state:

```text
Ситуация: <clean VM | existing Gateway>
Выбранный путь: <clean install | preserve-existing/update path>
Уже сделано: диагностика целевой среды
```

For this Yandex clean-install runbook, continue to Stage 2 only when the chosen path is `clean install`.

If an existing working Gateway is detected, stop the clean-install flow and do not run `bootstrap.sh` until the installer is confirmed safe for preserving the existing authentication, secrets, hostname, and Caddy configuration.

After diagnosis is closed, show the updated progress map.

## Stage 2 — create the VM in Yandex Cloud

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

Yandex Cloud requires the public half of the SSH key on the VM and the private half to remain with the user.

When VM creation is confirmed complete, mark Stage 2 `✅`, show the full progress map, and only then give the SSH step.

## Stage 3 — verify one SSH login

On the user's local macOS/Linux terminal, connect with the matching private key:

```bash
ssh -i ~/.ssh/<private-key-file> <username>@<public-ip>
```

If the host fingerprint prompt appears, verify/accept it once.

When the shell prompt on the VM appears, SSH is proven and the Yandex-specific infrastructure stage is complete.

Do not continue changing Yandex access settings after successful SSH login.

When SSH is confirmed, mark Stage 3 `✅`, show the full progress map, and only then give the installer command.

## Stage 4 — run the public installer

Inside the VM, run:

```bash
curl -fsSL https://raw.githubusercontent.com/0036111-lab/gateway-installer/main/install.sh | sudo bash -s -- --owner-email <owner-email>
```

This is the boundary between cloud provisioning and product deployment.

The installer obtains the repository and hands off to `bootstrap.sh`.

When the installer has started successfully, mark Stage 4 `✅` and show the progress map. The remaining stages are largely automated, but the LLM must still report each closed milestone when it becomes visible in the installer output.

## Stage 5 — host dependencies

`bootstrap.sh` installs:

- Python venv support
- Docker
- Docker Compose
- Caddy
- curl and required host packages
- the repository's `gateway` CLI

When these dependencies are confirmed installed, mark Stage 5 `✅` and show the progress map.

## Stage 6 — Gateway stack

`bootstrap.sh` then:

- detects the public IPv4
- chooses the final public URL
- runs `gateway setup`
- generates/preserves local system secrets as appropriate
- writes the private `.env`
- runs `gateway doctor`
- builds and starts PostgreSQL
- builds and starts Gateway
- starts the notification worker

When PostgreSQL and Gateway are running successfully, mark Stage 6 `✅` and show the progress map.

## Stage 7 — HTTPS

The bootstrap flow:

- creates an `sslip.io` hostname by default unless a hostname is supplied
- writes the Caddy reverse-proxy configuration
- obtains HTTPS automatically through Caddy
- exposes the Gateway through HTTPS while the Gateway port itself remains bound locally

When HTTPS is available, mark Stage 7 `✅` and show the progress map.

## Stage 8 — healthcheck

The installer verifies the public endpoint:

```text
https://<host>/healthz
```

Success requires JSON containing:

```json
{"ok": true}
```

When this is confirmed, mark Stage 8 `✅` and show the progress map.

## Stage 9 — final MCP URL

The deployment is complete when the installer prints the final MCP URL:

```text
https://<host>/mcp
```

Mark Stage 9 `✅` and show the final progress map:

```text
ПРОГРЕСС РАЗВЁРТЫВАНИЯ

✅ 1. Диагностика целевой среды
✅ 2. Создание VM в Yandex Cloud
✅ 3. Проверка SSH-доступа
✅ 4. Запуск installer
✅ 5. Docker / Docker Compose / Caddy
✅ 6. Gateway + PostgreSQL + worker
✅ 7. HTTPS / sslip.io
✅ 8. Healthcheck
✅ 9. Готовый MCP URL

Результат: https://<host>/mcp
```

## Important boundary

VM creation is an infrastructure step. Everything after the first successful SSH login should be handled by this repository's installer rather than by a long sequence of manual shell commands.

Authentication is intentionally separate from this smoke-test bootstrap. The current default bootstrap uses `auth none`; production authentication must be configured as a later stage.
