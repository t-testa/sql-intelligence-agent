# Implementation plan

## M1 — Local functional MVP (complete with mocked Azure OpenAI)

1. Scaffold the independent repository, pinned Python dependencies and local Docker services.
2. Create five synthetic tables, deterministic seed, metric definitions and approved reporting views.
3. Add a fail-closed T-SQL gateway and separate migration/runtime database identities.
4. Connect FastAPI, explicit Responses API proposal contracts, deterministic mock mode and SQL Server.
5. Add Streamlit chat, SQL/result inspection, charts, explanations and verified practice exercises.
6. Test 25 analytical questions against independent Decimal fixtures and privileged reference SQL;
   test malicious SQL, prompt injection, joins, limits, timeouts, authentication and Learning Mode.
7. Run lint, type checking, unit/security/evaluation/integration checks and a real local demonstration.

Completed October 8, 2026: 218 tests pass on Windows and Linux; 27/27 analytical cases match the
independent fixtures; 50/50 policy attempts are rejected. See [VERIFICATION.md](VERIFICATION.md).

## M2 — Secure Azure deployment (design and IaC only until owner approval)

Private VNet deployment, Entra users, managed identities, SQL and Azure OpenAI private endpoints,
monitoring, cost review, approved provisioning, database privilege audit and authenticated smoke tests.

## M3 — Fabric and Power BI (separate approved ingestion project)

Backend capability interface and compatibility review; explicitly approved Lakehouse ingestion;
curated tables, SQL editor workflow, SQL-aligned DAX measures and report design.

## M4 — Enterprise readiness

Delegated identity, row-level security, distributed limits, protected audit sink, red-team review,
governance and restore/incident exercises. M1 is a synthetic single-operator learning environment.

No cloud deployment, external publication or changes to other repositories are authorized.
