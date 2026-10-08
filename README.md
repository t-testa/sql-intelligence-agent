# SQL Intelligence Agent

**Ask an operations question, inspect validated T-SQL, explore the result and practice writing it yourself.**

A standalone portfolio and learning application using **Streamlit → FastAPI → SQL Server/Azure SQL**.
The model proposes SQL through the Responses API; application policy and database permissions decide
what can execute. All shipped data is synthetic and all financial amounts are CAD.

## Current status

M1 is implemented and tested with a real SQL Server 2022 Developer container and deterministic
Azure OpenAI mocks. The interface has chat, SQL inspection, result tables, optional charts, query
lessons and independent practice comparisons. Mock mode recognizes 27 documented example questions;
it does not claim unrestricted natural-language understanding.

M2 includes Entra token validation, managed-identity adapters, private Azure Bicep templates and a
deployment runbook. No Azure resources have been provisioned. M3/M4 remain future work; see the
[implementation plan](docs/IMPLEMENTATION_PLAN.md) and [readiness gaps](docs/READINESS.md).

## Quick start — Docker

Prerequisites: Docker Desktop with Linux containers and at least 4 GB available memory; Python 3.10–3.12
only to generate the local `.env`. No Azure credentials are needed for the demonstration.

```powershell
python -m scripts.init_local
docker compose --profile app up -d --build
```

Open **http://127.0.0.1:8501** and click **Ask this question** for “Show total invoiced by region.”
The backend is at http://127.0.0.1:8000; local API documentation is at `/docs`. Protected API endpoints
require the generated local bearer token. The frontend uses it server-side.

On this initial build, `.env` has already been generated and the local containers were started.
Initialization deliberately refuses to overwrite an existing `.env`.

| Region | Total invoiced (CAD) |
|---|---:|
| Central | 1,691,724.00 |
| East | 1,697,952.00 |
| North | 1,704,180.00 |
| West | 1,131,968.00 |

The source contains **60 customers, 240 jobs, 480 invoices, 720 expenses and 48 targets**.

## Local Python development

Install Microsoft ODBC Driver 18 for SQL Server. Use **127.0.0.1**, not `localhost`, if Windows resolves
localhost to IPv6 while Docker publishes IPv4.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.lock
python -m scripts.init_local  # only when .env does not exist
docker compose up -d --wait sqlserver
.venv\Scripts\python -m scripts.bootstrap_db
.venv\Scripts\python -m scripts.demo
```

Run these in separate terminals from the repository root:

```powershell
.venv\Scripts\uvicorn backend.api.main:create_app --factory --host 127.0.0.1 --port 8000
.venv\Scripts\streamlit run frontend/app.py --server.address 127.0.0.1
```

Stop the Docker API/frontend first if their ports are in use: `docker compose stop backend frontend`.
The Docker runtime never receives the administrator password; migration/test containers do.

## Verification

```powershell
.venv\Scripts\ruff check .
.venv\Scripts\ruff format --check .
.venv\Scripts\mypy
.venv\Scripts\python -m pytest -m "not integration"
$env:RUN_SQL_INTEGRATION='1'
.venv\Scripts\python -m pytest --junitxml=artifacts/tests.xml
.venv\Scripts\python -m scripts.evaluate
docker compose --profile test run --build --rm tests
```

SQL tests use a privileged local-only connection for independent reference queries and a rolled-back
timeout test. The API has no such capability. Windows sandbox restrictions may require allowing
localhost sockets for Pytest's in-process FastAPI client as well as SQL Server. See
[EVALUATION.md](EVALUATION.md) for measured results. GitHub Actions runs offline and Linux SQL Server
suites with a mocked model; no cloud keys or billable resources are needed.

## Azure OpenAI mode

Use an existing, approved Azure OpenAI resource and Responses-compatible deployment. Set
`AGENT_MODE=azure`, `AZURE_OPENAI_ENDPOINT` to its HTTPS resource origin and `AZURE_OPENAI_DEPLOYMENT`
to the deployment name. Local development can use an API key or developer Azure identity. Cloud mode
requires managed identity and Entra user authorization. Azure mode incurs inference charges.

The Docker app profile deliberately stays in mock mode; the new `compose.azure.yaml` override explicitly
enables local live inference. The adapter uses the standard OpenAI client with Azure's
`/openai/v1/` endpoint, strict function calling, one proposal tool, bounded output and `store=False`.
See the official [function-calling guide](https://developers.openai.com/api/docs/guides/function-calling)
and [Azure Responses guide](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/responses).

Follow [LIVE_AZURE_OPENAI.md](LIVE_AZURE_OPENAI.md) for exact configuration, Docker and host-identity
commands, conversation limits and the first-query verification helper. `--check-config` is offline;
`--allow-cloud-call` explicitly opts into one billable question. Live questions use the same gateway
and restricted database principal. The 27-question mock catalog remains unchanged.

## Repository map

| Directory | Responsibility |
|---|---|
| `backend/api` | Authenticated HTTP contracts, size limits and status handling |
| `backend/agent` | Proposal providers, orchestration, grounded answers and lessons |
| `backend/security` | Positive SQL policy, parameter compilation and Entra authentication |
| `backend/database` | SQLAlchemy/pyodbc, deadlines, bounds and backend interface |
| `backend/semantic` | Trusted view, column, grain and metric catalog |
| `frontend` | Streamlit interface; no direct database access |
| `sql` | Schema, approved views and independent expected fixtures |
| `scripts` | Separate privileged bootstrap, deterministic seed and evaluation |
| `tests` | Unit, security, integration and analytical evaluation suites |
| `infrastructure` | Undeployed private Azure foundation and API templates |

Documentation: [Architecture](ARCHITECTURE.md) · [Security](SECURITY.md) ·
[Threat model](THREAT_MODEL.md) · [SQL learning](SQL_LEARNING.md) ·
[Fabric and Power BI](FABRIC_INTEGRATION.md) · [Deployment](DEPLOYMENT.md).

Stop with `docker compose stop`. `docker compose down` removes this project's containers but preserves
data. Only when intentionally discarding this synthetic database, use `docker compose down -v`;
that last command deletes the named volume.
