# Final M1 verification — October 8, 2026

Historical build evidence below is superseded for current release status by
[October 8 live accuracy and release verification](RELEASE_VERIFICATION.md). Statements below about
unconfigured Azure or no billable inference describe the earlier preparation stage only.

## Live-inference preparation follow-up

The existing 218-test baseline was rerun unchanged before edits. After preparation, **275 tests pass**
on Windows (3.37 s) and Linux Docker (3.71 s), including all 218 original tests and 57 new checks.
Ruff lint/format passes (49 Python files), and strict mypy passes across 28 backend/script files.
The unchanged mock benchmark still reports **27/27** correct and **50/50** policy attacks rejected.
The Docker live override validates with dummy configuration values; it was not started in live mode.
The rebuilt API/UI/SQL containers are healthy in **mock mode**. Browser checks verified a result,
another request in the same conversation, and New conversation reset.

New evidence: `artifacts/baseline-live-prep.xml`, `artifacts/live-prep-tests.xml`,
`artifacts/live-prep-docker-tests.log`, `artifacts/tests.xml`, `artifacts/evaluation.json`, and
`artifacts/live-prep-ui.jpg`. The Azure configuration preflight correctly reports missing endpoint and
deployment. No resource provisioning, Azure credential validation or billable inference occurred.
See [the live runbook](../LIVE_AZURE_OPENAI.md) for the explicit first-query verification command.

## Original M1 record

All results below were observed locally. No cloud resources were deployed or existing project
repositories edited. The new independent Git repository is on branch `codex/m1-local-mvp`; no remote
repository or publication was created.

| Check | Actual outcome |
|---|---|
| Windows Python 3.10 full suite | **218 passed**, one upstream deprecation warning, 2.59 s |
| Linux Docker full suite | **218 passed**, same warning, 2.72 s |
| Real SQL execution benchmark | **27/27** match independently computed expected fixtures |
| Malicious/unauthorized SQL corpus | **50/50** rejected |
| Ruff lint | Pass |
| Ruff format check | 41 Python files formatted |
| Strict mypy | Pass across 26 backend/script source files |
| Azure foundation Bicep compilation | Pass; CLI only reports an available Bicep update |
| Azure application Bicep compilation | Pass; no deployment performed |
| Docker application build/start | Pass; SQL Server, API and frontend running with health probes |
| Browser demonstration | Regional invoice totals returned; independent practice comparison matched |
| Secret exclusion | `.env`, `.venv` and generated artifacts excluded by Git; `.env` excluded from images |

The signed Entra tests cover approved user, expired token, wrong audience/issuer/tenant, unapproved
user, wrong scope and app-role-only rejection. Real tenant sign-in and managed-identity authentication
still require M2 deployment verification. The warning is Starlette's deprecated AnyIO BlockingPortal
alias; no test failed because of it.

Generated evidence (ignored by Git):

- `artifacts/tests-windows.xml` — Windows JUnit result.
- `artifacts/tests.xml` — Linux JUnit result.
- `artifacts/docker-tests-final.log` — complete Linux run log.
- `artifacts/evaluation.json` — final mock accuracy and policy outcomes, 2026-10-08 14:09 UTC.
- `artifacts/demo.json` — actual question/SQL/result/learning demonstration.
- `artifacts/app-demo.png` — browser proof of the bounded result and optional chart.
- `artifacts/main.json`, `artifacts/application.json` — locally compiled ARM templates.

The application is available at **http://127.0.0.1:8501**. To review M1, click **Ask this question**,
then inspect Generated SQL and Learn & practice. No credentials are needed for that local mock demo.

To begin M2, the owner must choose and approve a dedicated Azure subscription/resource group/region,
cost envelope, Entra administrator group and authorized users, plus a Responses-compatible model
deployment. These are future deployment inputs, not blockers to the working local MVP.
