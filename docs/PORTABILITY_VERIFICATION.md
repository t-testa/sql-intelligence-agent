# Operating-mode verification — October 8, 2026

**Local portable deployment: verified. Private Azure deployment: prepared, not provisioned or verified.**
This report supplements the earlier finite live accuracy and private-auth reports. It does not promote
local results to Azure-hosted certification. No new Azure infrastructure, registration, role assignment,
collaborator access or public publication was performed in this portability task.

## Actual results

| Check | Observed result |
|---|---|
| Windows launcher | Stop and live start succeeded; SQL/API/UI healthy; existing volume/configuration retained |
| Ubuntu 22.04 WSL launcher | Status, live start and full Docker regression succeeded against the same Docker Desktop engine/container |
| Final native Windows suite | **466/466 passed**, 0 failures/errors/skips, 7.76 seconds |
| Final WSL/Docker suite | **466/466 passed**, 0 failures/errors/skips, 5.52 seconds |
| Mandatory security directory | **219/219** in each final suite, including 21 new deployment-tool checks |
| Original baseline | Original 218 and previous 443 tests preserved; no deleted/relaxed assertions |
| Fresh local live smoke | **2/2 SQL results correct**, all 240 rows independently verified for each; existing `sql-agent-model` |
| Final one-command live verification | Passed, including API provider check, generated ROW_NUMBER SQL, execution, oracle comparison and report export |
| Deterministic replay / independent references | **61/61 recorded cases / 53/53 query references**, no model calls in regression |
| Mock / adversarial corpus | **27/27 / 50/50 rejected** |
| SQL Learning Mode | Existing display/explanation/practice/independent comparison and security tests pass; no new exercises |
| Static checks | Ruff lint/format pass; 66 Python files formatted; strict mypy passes 39 source files |
| Bicep | Foundation, private DNS, API and frontend compile; none applied |
| Windows desktop shortcuts | Live, Mock and Stop installed; shortcuts contain launcher paths/arguments only |

The original 61-case live release corpus was not rerun against Azure SQL. The two new live smoke calls
exercise the same ranked-invoice question; they are not a new 61-question accuracy estimate. Inference
was explicitly invoked; startup, stop, configuration checks and replay made no model calls.
One upstream Starlette/AnyIO deprecation warning remains in each final suite.

## Failures investigated and corrections

1. Early Windows native SQL runs encountered connection/query timeout and cancellation failures during
   lifecycle testing. The driver could raise another error during rollback and mask the original timeout.
   Cleanup now invalidates a broken pooled connection, preserves the sanitized primary error and releases
   capacity. Two new regression tests cover this behavior. Query/row/byte/concurrency limits were not
   raised. A clean restart and sequential final Windows/Docker suites passed; the original intermittent
   transport/driver timing trigger was not conclusively isolated. Prior failed reports remain local.
2. The first new live SQL request succeeded and all rows were correct, but the workflow's `docker cp`
   step could not retrieve its report from the container's tmpfs. Export now reads only the named report
   through `exec`, validates JSON and writes a new local file. The first report was recovered and verified
   without another model call. Two regression cases cover successful export and malformed-report failure.
   The subsequent full one-command live workflow passed.
3. Windows' shared pytest temporary directory had an ACL conflict. A new repository-local scratch
   directory was used for the final native run; no machine/global permissions were altered. The portable
   Docker test workflow uses its container temporary directory and is the recommended repeatable path.

These are operational failure records, not omitted incorrect SQL results. Failed/partial attempts are
not counted as passing full regression runs. No expected output or accuracy denominator was changed.

## Evidence and preserved inputs

Ignored local artifacts include:

- `artifacts/portability-windows-final.xml` and `artifacts/tests.xml` for the final complete suites.
- `artifacts/portability-windows.xml` and `artifacts/portability-windows-recheck.xml` for earlier failures.
- `artifacts/portable-live-recovered-20261008T185610.json` and
  `artifacts/portable-live-20261008T190150566745Z.json` for the two actual live results.
- `artifacts/evaluation.json` for mock/security counts, and `artifacts/portable-*.json` for compiled templates.
- Private scratch/shortcut review files under `.local/` and `artifacts/`, excluded from Git.

Frozen evidence remains byte-for-byte unchanged:

| File | SHA-256 |
|---|---|
| `evaluation/cases.json` | `a0d9d4c0920c7cc6047bf1dc7a9ccf85d3d4251940e24e8fe3994a571e46cc1b` |
| `evaluation/recordings/accepted.json` | `8200b990442f10e655536240d4579983beff78e0ce2f571cbc2b8393d4a6a856` |

The local `.env`, its secrets, sole-owner allowlist and local database remain outside source control.
The temporary Azure plan preserves the existing OpenAI account and an approved local access path
outside the disposable application group. It includes post-cleanup local live/replay verification.

## Azure gates still open

The approved owner/tenant and private source repository are known. Actual Entra registrations, delegated
consent/assignments, stable private callback/TLS, browser/migration route and complete cost quote remain
predeployment gates. An exact private callback cannot be inferred from a not-yet-created ACA environment.
Existing-compatible environment reuse or a reviewed stable custom-domain binding is required to finish
that gate under the owner's current approval sequence.

After those checks, obtain explicit approval for the dedicated application inventory and narrow grants.
Only after provisioning can actual Entra login/revocation, MI, private routing, Azure SQL references/
replay/live accuracy, limits, Learning Mode and delivered alerts be tested. Cleanup requires a reviewed
inventory and separate deletion approval, including cross-group identity/network leftovers. No Azure
success, actual Azure operating cost, post-cleanup cloud observation or redeployment rehearsal is claimed.

Use [the Azure lifecycle runbook](AZURE_LAB_RUNBOOK.md) and
[local portable operations](LOCAL_PORTABLE.md). The application remains a finite, bounded learning and
analytics system; universal SQL correctness and zero hallucinations are not claimed.
