# Live accuracy and release verification — October 8, 2026

**Local acceptance passed. Azure hosting is not yet a validated release.**

This preserves the accuracy-validation record. The later private-by-default work adds cloud-token
handoff and access tests: **443/443 regressions and 198/198 security tests now pass on both platforms**.
For current identity, GitHub and deployment blockers, use [private verification](PRIVATE_VERIFICATION.md).
Historical 367-test counts below refer to the original live accuracy validation stage.

The application genuinely used the existing **sql-agent-model** deployment. The final fresh live run
passed **61/61 cases (100%)**: **53/53 complete analytical results** and **8/8 clarification/refusal
outcomes**. All **367 regression tests passed on Windows and Linux**, preserving the original 218-test
baseline. SQL Learning Mode remains a permanent feature. No additional Azure resources were created
and no public access was enabled.

This is a finite, synthetic, development acceptance corpus, improved after investigating failures.
It is not a held-out generalization benchmark, proof of arbitrary SQL correctness or a zero-hallucination
claim. The deployment blockers below remain release gates.

## Live inference evidence

| Item | Observed value |
|---|---|
| Deployment requested and returned | sql-agent-model |
| Underlying model/version | gpt-4.1-mini / 2025-04-14 |
| Region / SKU | Canada East / GlobalStandard, capacity 20 |
| Published deployment limits | 20 requests/minute, 20,000 tokens/minute |
| Final run UTC | 2026-10-08 16:32:42–16:44:55 |
| Final live input/output tokens | 98,682 / 3,367; 89,088 input tokens cached |
| Final response count | 61 actual Azure responses, each with response/request IDs |
| Pacing/output cap | 12 seconds between calls; 1,000 maximum output tokens |
| Automatic retries / mock fallback | None / none |

The [sanitized Azure inventory](../evaluation/azure-inventory.json) maps the deployment to the model.
The [accepted recording](../evaluation/recordings/accepted.json) contains actual SDK receipts, raw
tool-call arguments, proposals, validated SQL, complete results, narration and per-case outcomes.
The initial authenticated API smoke check independently verified the requested ROW_NUMBER highest-invoice
query: **240 jobs**, correct amounts and deterministic invoice ties. Local evidence is in
`artifacts/phase1-live-smoke.json`.

The provider already existed; it was extended and tested rather than replaced. Both live and mock
proposals still use `AgentService → SQLGateway → SQLServerBackend`. The model has no execution tool
or direct database credentials. Conversation context carries bounded accepted questions/proposals and
clarifications, never result cells; ownership and expiry tests pass.

## Transparent run history

| Run | Passed / cases | Failure rate | What failed |
|---|---:|---:|---|
| Initial unpaced batch | 35/61 | 42.62% | 22 Azure throttles, 1 invalid proposal contract, 3 SQL policy rejections |
| Paced correction run | 56/61 | 8.20% | 2 invalid contracts, missing explicit JOIN, incorrect RANK ties, unsupported date function |
| Targeted fixes | 4/5 | 20.00% | Explicit requested JOIN still omitted |
| JOIN retest | 1/1 | 0% | None |
| Full candidate | 60/61 | 1.64% | Overall-average query used a prohibited comma/CROSS JOIN |
| **Fresh final confirmation** | **61/61** | **0%** | **None in this run** |

All recordings are retained under [evaluation/recordings](../evaluation/recordings). Targeted retests
are not presented as full-suite accuracy. The final score is a single fresh run of every case with the
same prompt and tool contract, not a collection of best answers from earlier runs.

Root causes and fixes:

- **Quota:** unpaced requests and a larger output reservation exceeded the existing small deployment.
  Added pacing, a 1,000-token cap, application rolling request/token/daily budgets, and stop-on-429 in
  the harness. No quota increase or resource provisioning was used.
- **Schema/grain:** the model placed Region on vJobs or attempted regional expense-detail joins.
  Clarified view columns and approved pre-aggregated metric sources in trusted instructions.
- **Contract:** query explanations appeared in the clarification field, or defined totals were treated
  as ambiguous. Reinforced mutually exclusive query/clarify fields and documented metric semantics.
- **Learning requirements:** a numerically equivalent single view omitted a requested JOIN. Explicit
  construct requirements are checked; prompt/tool field guidance now preserves them.
- **Ranking:** adding InvoiceId inside RANK incorrectly split equal-amount ties. The instructions and
  lessons distinguish ROW_NUMBER tie-breaking from RANK/DENSE_RANK equal-value semantics.
- **Supported SQL subset:** DATEPART and comma joins were outside policy. The prompt specifies supported
  MONTH/YEAR extraction and scalar subqueries. The gateway was not weakened to accept these proposals.
- **Practice precision:** candidate/reference comparison previously rounded to cents and ignored order.
  It now compares exact numeric values and honors independent reference ORDER BY; regressions prove
  fractional count errors and reversed ordering cannot pass.
  A final review also replaced context-sensitive Decimal normalization so values with more than 28
  significant digits retain full SQL DECIMAL(38) precision; its regression passes on both platforms.
- **Safe diagnostics:** configuration validation now hides input values, preventing a malformed setting
  from dumping configured credentials into an exception log.

No expected result was changed to make a live answer pass. The frozen fixture hash is
`a0d9d4c0920c7cc6047bf1dc7a9ccf85d3d4251940e24e8fe3994a571e46cc1b`.
Final prompt hash: `12d49c12469759bf6944694823166aea1e1588ae04d1eb62297d0acc53a52a39`.
Final tool-contract hash: `d79079d38508025b069e72a9d20f9ef9c12f92f32994b512a9eef428dbfb609f`.

Across the six recorded development/retest runs there were 250 attempted cases and 228 completed Azure
responses. Receipt-based inference cost is approximately **US$0.073**, including cached-token pricing.
This is an estimate, not an Azure invoice; it excludes separate API/UI smoke calls and infrastructure.
The initial report's top-level token counters omitted one contract-invalid response; the corrected
[summary](../evaluation/summary.json) totals every response receipt without altering the original file.

## Independent correctness and security gates

| Gate | Actual result |
|---|---|
| Independently written SQL versus deterministic expected outputs | **53/53 match** |
| Fresh live analytical query accuracy | **53/53 match** |
| Clarification/unsupported/adversarial behavior | **8/8 clarify/refuse; no SQL executed** |
| Recorded replay | **61/61 pass, zero Azure calls** |
| Windows full suite | **367 passed**, 0 failed/errors/skipped, 4.34 s |
| Linux Docker full suite | **367 passed**, 0 failed/errors/skipped, 4.29 s |
| Tests in mandatory security directory | **122/122 pass on each platform** |
| Direct database-denial tests bypassing application policy | **6/6 pass on each platform** |
| Existing mock evaluation / attack corpus | **27/27 correct / 50/50 rejected** |
| Separate offline run before the final precision regression | **210 passed**, 156 SQL integration tests deselected |
| Ruff / formatting / strict mypy | Pass |
| Updated application Bicep | Compiles; not deployed |

The SQL runtime is actually `sql_runtime`, not dbo/sysadmin/db_owner. Startup verifies the expected
principal and permission probes. Tests connect with runtime credentials directly, bypassing the SQL
validator, and demonstrate denied base-table/internal-field reads, UPDATE/DELETE, view writes and
object creation. Thus read-only access is enforced by SQL Server as well as application policy.

Security coverage includes unauthorized schemas/columns, prompt injection, system/unsafe functions,
multi-statement modification and privilege changes, expensive/cross/fanout joins, ranked-join bypasses,
typed parameter injection, actual driver/lock deadlines, concurrency and row/byte limits. Excess results
fail visibly and do not produce partial summaries. No aggregate is calculated from hidden truncated rows.
Signed-token tests cover issuer/audience/expiry/tenant/user/scope; they are local cryptographic tests,
not proof of the future tenant's live Entra configuration.

Expected results come from independent Python Decimal calculations and separately authored reference SQL
over deterministic baseline and edge fixtures. The edge database covers absent invoices/expenses,
customers without jobs, tied/duplicate invoice amounts, zero denominators and cent-level values. NULLs
from missing joins/empty aggregates are distinguished from zero. Full result multisets, order where
specified, exact precision and required constructs are checked. Result explanations are deterministic
and checked against executed values; no model grades its own answers. See [methodology](../EVALUATION.md).

One upstream Starlette/AnyIO deprecation warning remains on both platforms; it does not fail the suite.
No unresolved critical/high defect was found in the tested local path. This is not a formal security
certification or a claim that all possible defects have been excluded.

## Learning Mode and portfolio evidence

Generated SQL, bound parameters, construct explanations, practice exercises, alternative-query checks
and independent verification remain implemented. All practice queries traverse the production gateway
and runtime identity. Additional adversarial practice cases cannot reach the executor. A correct
alternative passes, while wrong values, tiny numeric differences, wrong required order and unsafe SQL fail.

The README contains architecture, capabilities, screenshots, security, reproducible evaluation, Learning
Mode examples, cloud instructions and limitations. Screenshots contain only synthetic data. Git/Docker
ignore private environment files, artifacts and local dependencies. A scan of publishable candidates
against the configured credentials found no matches; this targeted scan is not a universal secret scanner.
No repository content was pushed or published during this validation task.

Browser verification in live mode returned the four correct regional invoicing totals, displayed the
generated SQL and retained the Learning Mode toggle. An alternative SUM expression passed the independent
reference comparison; the UI showed the reference SQL and complete result table. See the
[live SQL screenshot](images/live-query.jpg) and [practice verification screenshot](images/learning-mode.jpg).

## Deployment decision and remaining blockers

**GO for continued local portfolio demonstration with live Azure inference and deterministic replay.**
**NO-GO for claiming a validated Azure-hosted release today.**

1. **Actual cloud authentication is unverified.** The later private-access adapter and offline tests
   are implemented. Approved tenant/user/registration IDs and real platform login/renewal still need
   verification. Do not substitute a local shared bearer token.
2. **Cloud infrastructure/identity acceptance is outstanding.** The tests used real local SQL Server
   2022 Developer. Repeat permission, reference, replay, timeout and live acceptance checks on the
   approved Azure SQL instance; verify actual MI, tenant auth, networking/DNS/TLS and token renewal.
3. **Deployment configuration and monitoring need final approval/validation.** Review the reuse-first
   topology, immutable registry images, ingress settings, alert delivery and persistent quota needs.
   The process-local daily budget resets on restart and cannot guarantee a cloud spending ceiling.
4. **Owner approval is required for billable resources, access grants and showcase contents.** The
   revised plan is private by default, keeps source PRIVATE and now reuses the existing OpenAI account.
   Identity/predeployment gates must finish before provisioning approval is requested.

The [private Azure plan](AZURE_RELEASE_PLAN.md) supplies a reuse strategy, revised cost scenarios,
authentication/rate/monitoring requirements,
approval sequence and cleanup instructions. The [live runbook](../LIVE_AZURE_OPENAI.md) provides exact
local configuration, launch, first-query verification and zero-charge replay commands.
