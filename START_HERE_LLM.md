# START HERE — LLM-assisted Gateway deployment

Use this file when the assistant cannot open GitHub or use a GitHub connector. The human can upload this file directly into any chat and ask the assistant to follow it.

## Goal

Take a user from a VM to a working public MCP endpoint with the shortest safe path.

## Mandatory operating rules

- Use one primary route from start to finish.
- Give only one next action at a time.
- Always say WHERE the action is performed: cloud UI, local terminal, or VM terminal.
- Do not repeat steps that are already proven.
- Do not ask the user to paste private keys, OAuth secrets, tokens, or passwords into chat.
- Do not touch an existing production Gateway unless the user explicitly chose an upgrade path.
- If one step fails twice, stop repeating it and diagnose the exact cause before changing approach.
- After every completed action, show the full progress map below with updated status.

## Progress map

Use exactly these stages and update them after every completed action:

```text
PROGRESS

⬜ 1. Diagnose target environment
⬜ 2. Create / confirm VM
⬜ 3. Verify SSH
⬜ 4. Run public installer
⬜ 5. Install Docker / Compose / Caddy
⬜ 6. Deploy Gateway + PostgreSQL + worker
⬜ 7. Configure HTTPS
⬜ 8. Healthcheck
⬜ 9. Show final MCP URL
```

Status markers:
- ✅ completed
- ▶️ current
- ⬜ not started

After the map always write:

```text
Current: <one short sentence>
Next: <one concrete action>
Where: <cloud UI | local terminal | VM terminal>
```

## Stage 1 — Diagnose target environment

First determine only what is necessary to choose the safe route:

- Is this a clean VM or an existing server?
- Does `/opt/gateway-platform` already exist?
- Is Gateway already running?
- Is Docker already installed?
- Is Caddy already installed?
- If Gateway exists: is authentication already enabled, and is there an existing hostname / HTTPS configuration?

Do not modify anything during diagnosis.

### Route decision

If the VM is clean and no Gateway installation exists, choose:

`clean install`

If an existing Gateway is already running, stop before running the bootstrap installer and state:

`existing installation detected — preserve current auth, secrets, hostname and Caddy before any upgrade`

Do not run the clean-install bootstrap over an existing production Gateway unless the installer has been explicitly prepared for that upgrade scenario.

## Stage 2 — VM requirements

For Yandex Cloud or another provider, the VM should have:

- Ubuntu 24.04 LTS or compatible Debian-based Linux
- 1–2 vCPU
- at least 2 GB RAM
- at least 20 GB disk
- public IPv4
- SSH access with a normal SSH key
- inbound TCP 22, 80 and 443 allowed

For Yandex Cloud, prefer a normal SSH key path for this runbook. Do not switch to OS Login unless the normal SSH route is proven blocked.

## Stage 3 — Verify SSH

From the user's local terminal:

```bash
ssh -i ~/.ssh/<private-key-file> <username>@<public-ip>
```

One successful shell prompt on the VM is enough. After SSH works, do not keep changing cloud access settings.

## Stage 4 — Run the public installer

On the VM terminal, run:

```bash
curl -fsSL https://raw.githubusercontent.com/0036111-lab/gateway-installer/main/install.sh | sudo bash -s -- --owner-email <owner-email>
```

The user executes this command. The assistant does not need GitHub access to guide this step.

The command downloads the public installer and hands off to `bootstrap.sh`.

## Stages 5–8 — What the installer should do automatically

The installer should:

1. install Docker and Docker Compose;
2. install Caddy;
3. install the `gateway` CLI;
4. detect the public IPv4;
5. create an `sslip.io` hostname by default;
6. run `gateway setup`;
7. run `gateway doctor`;
8. build and start PostgreSQL, Gateway and notification worker;
9. configure HTTPS;
10. verify the public `/healthz` endpoint.

Do not replace this automated path with a long list of manual shell commands unless the installer fails and the exact cause has been identified.

## Stage 9 — Success criteria

Installation is complete when the public health endpoint returns JSON containing:

```json
{"ok": true}
```

Then show the user the MCP endpoint:

```text
https://<hostname>/mcp
```

Also state the current authentication mode. The current clean-install bootstrap may use `auth none` for smoke testing; production authentication is a separate stage.

## Example progress update

```text
PROGRESS

✅ 1. Diagnose target environment
✅ 2. Create / confirm VM
✅ 3. Verify SSH
▶️ 4. Run public installer
⬜ 5. Install Docker / Compose / Caddy
⬜ 6. Deploy Gateway + PostgreSQL + worker
⬜ 7. Configure HTTPS
⬜ 8. Healthcheck
⬜ 9. Show final MCP URL

Current: SSH is confirmed and the VM is clean.
Next: Run the public installer command.
Where: VM terminal.
```

## Repository

Public repository:

https://github.com/0036111-lab/gateway-installer

Public installer entrypoint:

https://raw.githubusercontent.com/0036111-lab/gateway-installer/main/install.sh

The assistant does not need to open these links if this file was uploaded directly into the chat; it can guide the user from the instructions above.
