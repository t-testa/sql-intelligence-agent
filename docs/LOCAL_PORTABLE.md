# Local portable deployment

This mode runs SQL Server, FastAPI and Streamlit in local Linux containers. Live inference reuses the
existing Azure OpenAI deployment; mock and recorded replay need no Azure calls. SQL Learning Mode,
the SQL gateway, restricted SQL identity, financial precision and bounded complete results are unchanged.
Azure application hosting and its resource group are not dependencies of this mode.

## Prerequisites and first setup

Use Windows with Docker Desktop's WSL 2 backend, Ubuntu WSL integration enabled, Linux containers,
and Python 3.10–3.12. The launcher itself uses only Python's standard library; an existing Windows
`.venv` is preferred, otherwise `py -3` is used. Ubuntu uses `python3`. Docker builds the pinned
application dependencies. Start Docker Desktop first; the launcher does not install software, change
Docker contexts or silently switch to a remote daemon. Allocate enough memory for the SQL container's
3 GiB limit plus API/UI, Docker and the host. The SQL image targets x86-64.

Keep the checkout in one location and use one Docker Desktop engine. This repository currently works
from its Windows path and `/mnt/c/...` path in Ubuntu. For frequent Linux development, a checkout in
the Ubuntu filesystem is preferable for bind-mount performance; see
[Docker's WSL guidance](https://docs.docker.com/desktop/features/wsl/best-practices/). Do not run two
copies concurrently: this project deliberately uses fixed loopback ports and a fixed Compose name.

On a fresh clone, start mock mode once. The launcher creates `.env` with unique local credentials only
if missing; it never overwrites an existing file. Privately set the following fields in `.env` before
live startup, leaving SQL credentials and the local bearer token intact:

```dotenv
AZURE_OPENAI_ENDPOINT=https://YOUR-EXISTING-RESOURCE.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=sql-agent-model
AZURE_OPENAI_API_KEY=YOUR-EXISTING-RESOURCE-KEY
AZURE_OPENAI_MAX_OUTPUT_TOKENS=1000
```

Do not paste real values into Git, shell arguments, screenshots or reports. Local SQL passwords and
the volume must be preserved together. Deleting `.env` while retaining the volume does not reset SQL
credentials; restore the matching private configuration. The template retains `AGENT_MODE=mock`;
the explicit live override changes the container provider without rewriting `.env`.

## One-command operations

From PowerShell at the repository root:

```powershell
.\local.cmd start --mode live --open-browser
.\local.cmd stop
```

From Ubuntu WSL at the same checkout:

```bash
bash ./local.sh start --mode live
bash ./local.sh stop
```

Other operations work with either wrapper:

```powershell
.\local.cmd start --mode mock
.\local.cmd status
.\local.cmd test
# Explicitly authorizes one billable model query, not resource provisioning:
.\local.cmd verify-live --allow-cloud-call
```

Start builds the image, checks loopback bindings and credential separation, waits for healthy SQL/API/UI
and validates live configuration without submitting a query. It opens `http://127.0.0.1:8501/` only when
requested. The backend remains authenticated with the generated local bearer token; the frontend
does not receive SQL or OpenAI credentials. This mode trusts the desktop operator and must not be
exposed through a tunnel, LAN port binding or public proxy.

`test` creates/verifies the separate local edge database and runs the complete suite, independent
references, recorded live replay and mock/adversarial checks with live credentials cleared. Run SQL
tests sequentially; Compose initialization can restart services and the SQL cancellation tests use
locks. Reports are `artifacts/tests.xml` and `artifacts/evaluation.json`. A failed operation returns
nonzero; raw Docker/Compose output is suppressed because it may contain configuration values.

`verify-live` checks the running provider, asks the highest-invoice question through FastAPI, and
compares all rows with an independent oracle. It saves `artifacts/portable-live-<UTC timestamp>.json`.
It refuses mock mode and does not retry failed inference. A successful startup alone does not prove
model connectivity or answer accuracy. See the [live runbook](../LIVE_AZURE_OPENAI.md) for troubleshooting.

Stop retains containers, images, the `sql-data` named volume, `.env`, code and evaluation evidence.
Starting again reuses the data. Ordinary stop never uses `down -v`, prunes Docker, or deletes files.
Recreating from zero uses the deterministic seed; only intentionally delete this project's volume
after backing up any wanted data and separately approving that deletion.

## Optional Windows desktop shortcuts

Run once from PowerShell to create Live, Mock and Stop shortcuts on your Desktop:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_desktop_launchers.ps1
```

The process-only policy option does not change machine execution policy. An organization-enforced
policy still applies. The script refuses to overwrite existing shortcuts. It stores only the local
launcher path and arguments, never credentials. The terminal stays open to show status/errors. Moving
the repository requires recreating the shortcuts. `-Destination <existing directory>` allows private
review before copying them to the Desktop. No shortcut is installed automatically on another account.

## Portability, backup and Azure cleanup

Preserve the private Git repository, locked dependencies, Dockerfile/Compose files, deterministic seeds,
frozen evaluation records and this runbook. Keep an encrypted owner-controlled backup of `.env` outside
the Azure application group, plus any wanted SQL data. A fresh synthetic install does not require an
Azure SQL export; the checked-in seed is the source of truth. An optional locally saved Docker image
can reduce dependence on a later package/base-image download, but must remain private.

The existing model must stay outside the temporary Azure application group. Local inference still
requires that model, a valid credential, approved network access and available quota. Do not disable
its existing key/network access as an unreviewed side effect of private Azure deployment. Cloud uses
its private endpoint and MI; the owner's local authenticated path is reviewed separately. If the
model becomes private-endpoint-only, a retained private route is required and has its own cost; full
application-group deletion must not be claimed to preserve live portability without testing that path.

After Azure cleanup, run `start --mode live`, the paid one-query verification if approved, `test`, and
`stop`. Record the results outside Azure. Frozen replay continues to work even when Azure inference
is unavailable; it is always clearly labelled as replay/mock, never presented as live inference.
