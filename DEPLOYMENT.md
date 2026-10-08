# Deployment and operations

## Two supported operating modes

The **temporary private Azure lab** provides real Entra, managed identity, private networking, Azure
SQL and monitoring experience. It is verified only after actual cloud acceptance. The **local portable
deployment** runs the same application in Docker Desktop/Ubuntu WSL, using local SQL Server and the
existing Azure OpenAI deployment. It remains usable after deletion of the dedicated Azure application
group. SQL Learning Mode, mock mode, independent references and deterministic replay remain permanent.

- [Local launch, stop, replay and Windows desktop shortcuts](docs/LOCAL_PORTABLE.md)
- [Azure provisioning, acceptance, evidence, rollback, cleanup and redeployment](docs/AZURE_LAB_RUNBOOK.md)
- [Dated verification of both modes](docs/PORTABILITY_VERIFICATION.md)

```powershell
.\local.cmd start --mode live --open-browser
.\local.cmd stop
.\local.cmd test
```

Ubuntu WSL uses `bash ./local.sh` with the same arguments. Start submits no inference request; questions
in live mode are billable. The reused model stays outside the temporary application group, with an
independent approved local access path. New Azure provisioning/deletion still needs explicit approval.

The full source repository is private. Azure uses an internal Container Apps environment, owner-only
Entra sign-in, independent FastAPI authorization and private SQL. The controlling documents are the
[private release plan](docs/AZURE_RELEASE_PLAN.md), [identity runbook](docs/PRIVATE_AUTH.md) and
[current verification](docs/PRIVATE_VERIFICATION.md). No provisioning, grants or publication are automated.

## Local development

`docker compose --profile app up -d --build --wait` starts synthetic SQL Server, migration, API and UI.
Ports bind only to 127.0.0.1 (14339/8000/8501). Local mode uses a generated bearer token for the one
trusted desktop operator. Cloud frontend configuration rejects this shared token; FastAPI checks Entra.
SQL Learning Mode stays available. Use [the live runbook](LIVE_AZURE_OPENAI.md) for already-authorized
inference; preserve mock mode for free regressions. Future private OpenAI cutover requires review.

```powershell
# No model calls: fixtures, references, recorded replay, security and Learning Mode.
docker compose --profile test run --build --rm tests
# Compilation only, not deployment.
az bicep build --file infrastructure/main.bicep --outfile artifacts/private-main.json
az bicep build --file infrastructure/private_dns.bicep --outfile artifacts/private-dns.json
az bicep build --file infrastructure/application.bicep --outfile artifacts/private-api.json
az bicep build --file infrastructure/frontend.bicep --outfile artifacts/private-frontend.json
# Missing approved identity configuration returns nonzero.
.\.venv\Scripts\python.exe -m scripts.private_preflight
```

Copy `infrastructure/private-preflight.example.json` to ignored `.local/private-preflight.json`, using
only explicitly approved identities. `--read-cloud` uses GET/read metadata checks; no login, grants or
provisioning. If GitHub CLI is unavailable, use connected GitHub metadata and retain separate evidence.
Never put secrets in command arguments, committed parameters or logs.

Templates are compiled, not applied. Identity setup and predeployment checks must finish before a
provisioning request. Actual private platform sign-in, network and Azure SQL acceptance follow approved
provisioning, before application use. API access is disabled by default. Local passing tests do not
establish a validated Azure release.

## Operations and cleanup

`/health` is minimal liveness. SQL permissions are checked at API startup. Compose API/UI containers
have read-only filesystems and dropped capabilities. Keep one API process for global limits. Avoid
HTTP/SDK debug logging. `docker compose stop` stops locally; `docker compose down` preserves data.
Use `docker compose down -v` only to intentionally delete this project's synthetic database. Cloud
cleanup needs inventory/deletion approval; preserve the reused OpenAI resource and needed evidence.
GitHub source revocation and application revocation are separate operations.
