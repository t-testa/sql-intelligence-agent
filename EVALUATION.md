# Evaluation

## Method

The 27 analytical questions in `backend/agent/examples.py` exercise sums, counts, filters, grouped
ratios, safe joins, subqueries, HAVING, CTEs and window ranking. The deterministic provider returns
proposals only; it contains no expected result values. Azure OpenAI calls are mocked in CI.

Expected results are committed in `sql/seeds/expected_results.json`. `scripts/build_fixtures.py` computes
them independently from source records using Decimal arithmetic; it never imports the proposal catalog
or invokes a model. Separately authored reference SQL is checked against those fixtures through both
approved views and a privileged base-table oracle using correlated aggregates. Tests never regenerate
fixtures. Rebuilding fixtures is an explicit reviewed dataset change.

Comparison uses column positions and unordered row multisets, retaining duplicates; numerical values
are compared to two decimals. SQL margin percentages use percentage points, while the DAX reference
uses a fractional ratio formatted as a percentage. These are fixture checks, not SQL equivalence proofs.

## Actual run, October 8, 2026

The first full Windows and Linux container runs each passed **210 tests**. Both used real SQL Server
2022 Developer with ODBC Driver 18; no SQLite substitute was used. The analytical evaluation achieved
**27/27 correct (100%)** and the policy corpus rejected **50/50 attempts (100%)**. This measures the
mock-to-policy-to-database pipeline, not an Azure model's generalization accuracy.

Covered evidence includes:

- Database-level denial of base/internal reads, writes, and object creation.
- 50 policy attempts: DML/DDL, dynamic SQL/procedures, external/system sources, hidden columns,
  multi-statement batches, hints, recursive queries, unknown functions and unsafe joins.
- Direct prompt injection in model proposals and instructions embedded in returned database values.
- Fanout proof: an invoice/expense detail join produces 3× invoices and 2× expenses; approved totals
  match independently summed base tables.
- Wrong average-of-percentages detection, deterministic seed integrity and metric identities.
- Driver/server deadline cancellation while a test transaction holds an exclusive lock; rollback
  preserves the seed. Row and byte limits reject excess results; the connection remains reusable.
- Authentication, spoofed-header rejection, body limits, clarification, proposal revalidation and
  Learning Mode comparison against an independent reference.
- Browser workflow: a real regional invoicing answer and a successful practice comparison.

Additional signed Entra-token tests were added after that initial run; the final verification record is
in [docs/VERIFICATION.md](docs/VERIFICATION.md). JUnit XML and machine-readable evaluation output are
generated under ignored `artifacts/`. One upstream Starlette/AnyIO deprecation warning was observed;
it did not fail tests. Ruff and strict mypy checks are part of verification. Both Bicep templates are
compiled locally; compilation does not deploy or verify cloud resources.

## Failures found and resolved during development

SQLGlot represents TOP with an empty options node and can flag unqualified subqueries as correlated
before qualification. The validator now checks actual TOP options and correlation after scope
qualification. Host SQL connectivity required 127.0.0.1 because the Docker binding is IPv4. The
timeout fixture now forces an exclusive table lock instead of relying on a no-op update. Windows
sandboxing blocks asyncio's internal sockets, so the API test suite ran with approved local access.

## Reproduce and extend

Live-inference preparation on October 8 added **57 tests**, preserving the original **218**; the full
suite now passes **275/275** on Windows and Linux. Four questions outside the mock catalog cover highest
invoice per job, latest invoice, grouped customer/job joins with HAVING, and windowed SUM/LAG. Their
hand-authored Azure response fixtures exercise the actual SDK with an offline HTTP transport, and the
provider/gateway/real SQL Server path against independent Python seed calculations. No new question
was added to MockProvider. Additional checks cover rank ties, empty invoice matches, unsafe join
variants, conversation ownership/clarifications/expiry, provider diagnostics and nonbillable preflight.
These are deterministic application tests, **not a measured live model generalization score**.

Run `python -m scripts.evaluate` after seeding, or `docker compose --profile test run --build --rm tests`.
Add each new question with an independently authored SQL reference and expected fixture, then review
its metric definition and grain. For live Azure evaluation, record deployment/model version, prompt
version, cost/tokens, exact candidate SQL, policy decisions, execution result and clarification outcomes.
Run a held-out paraphrase/ambiguity set; do not report this deterministic mock score as model accuracy.
