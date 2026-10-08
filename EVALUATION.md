# Accuracy and security evaluation

See [release verification](docs/RELEASE_VERIFICATION.md) for actual live scores, failures, test totals
and the separate cloud deployment decision. A passing finite corpus is not universal SQL correctness.

## Independent oracles

`evaluation/cases.json` freezes **61 cases: 53 queries and 8 clarification/refusal cases**. Its SHA-256 is
`a0d9d4c0920c7cc6047bf1dc7a9ccf85d3d4251940e24e8fe3994a571e46cc1b`. Twenty-seven queries retain the
original baseline; twenty-six add previously unseen requirements. No new case was added to MockProvider.

`scripts/release_cases.py` independently calculates expected results from deterministic source records
with Python Decimal arithmetic and separately authored SQL. It does not use generated proposals or ask
a model to supply expected results. SQL references read both reporting views and privileged base tables
in the test harness. The runtime API never receives those administrator credentials. All 53 reference
SQL queries must match the frozen expectations before measuring generated SQL.

The normal synthetic database has 60 customers, 240 jobs, 480 invoices, 720 expenses and 48 targets.
`scripts.bootstrap_validation` creates a second local database, **SQLIntelligenceValidation**, with the
same schema and restricted runtime identity. Its four jobs include tied invoices, zero-valued invoices,
missing invoices, missing expenses, cent-level amounts and a customer without a job. It does not replace
the application's demo data. Source amounts are NOT NULL; tested NULLs arise from outer joins, empty
aggregates and zero denominators, not nullable source amounts absent from the schema.

## What is checked

| Area | Coverage |
|---|---|
| Basic analysis | Filters, counts, sums, averages, status/region/category groups, HAVING |
| Relationships | Job/customer joins, ranked invoice join, jobs without invoices, customer with no job |
| Financial correctness | Ratio of totals, zero denominator, negative margin, budget variance, exact cents |
| Advanced SQL | CTE, uncorrelated subquery, ROW_NUMBER, RANK ties, LAG, running SUM/ROWS, month comparison |
| Grain and missing data | Invoice/expense fanout prevention, duplicate amounts, COUNT DISTINCT, empty SUM/COALESCE |
| Language behavior | Ambiguous revenue/success, unavailable payroll/cash data, injection/refusal cases |
| Completeness | Entire bounded result, row count, duplicate multiplicity, NULL versus zero, ordered ties |

The live harness calls the real `AzureResponsesProvider`, then the production `SQLGateway` and
`SQLServerBackend` under `sql_runtime`. It requires the requested SQL construct, exact output columns,
exact numeric values, complete row multisets and specified ordering. It does not round away financial
errors, add hidden TOP limits or accept partial results. For denials, any query proposal fails the case;
such proposals are validated but never executed by that test case.

Natural-language result summaries are deterministic functions of executed cells/columns/row counts.
An independent grammar check rejects extra or invented factual claims. SQL lessons describe parsed
constructs and trusted metric definitions; they are not model-written correctness judgments. Clarify/
refusal wording is retained for review. There is no LLM-as-judge or model self-grading.

## Evidence and failure handling

`evaluation/recordings/` retains actual live runs, including unsuccessful runs. Each result contains
the question, raw proposal, policy outcome, complete executed result where permitted, failure category,
Azure response/request IDs, requested deployment, returned model field and token usage. The report
also records prompt, tool-contract and fixture hashes. No keys, connection strings or customer data
are included. The model/version mapping comes from the separate sanitized Azure inventory.
Git attributes preserve evaluation-file bytes across Windows/Linux checkout, including the newline
encoding used when those provenance hashes were recorded.

The initial batch remains visible: rapid requests hit quota; schema/contract mistakes also occurred.
Later runs corrected pacing, the prompt and explicit teaching requirements. Fixes did not change the
frozen expected results, relax the SQL gateway or silently substitute a mock answer. These are
development/acceptance measurements after inspecting failures, not an untouched holdout benchmark.
Repeating a prompt can still produce different SQL and can fail later.

Failure classes include provider/contract failure, Azure throttling, policy rejection, execution failure,
unexpected clarification, missing requested construct, column mismatch, completeness, precision/NULL/
duplicates, ordering and unsupported narrative. Investigate failures before retrying; preserve both
recordings. The harness stops on 429 and has an explicit call/token budget, with no automatic retries.

## Reproduction without cloud charges

```powershell
docker compose up -d --wait sqlserver
.\.venv\Scripts\python.exe -m scripts.bootstrap_validation
.\.venv\Scripts\python.exe -m scripts.release_eval --mode references --output artifacts/reference-check.json
.\.venv\Scripts\python.exe -m scripts.release_eval --mode replay --recording evaluation/recordings/accepted.json --output artifacts/replay-check.json
$env:RUN_SQL_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest -q --junitxml=artifacts/tests-windows.xml
docker compose --profile test run --build --rm tests
```

The full regression suite executes the recorded proposals against real SQL Server, revalidates them,
and recomputes the comparisons. Replaying is deterministic and makes **zero model calls**; it proves
the application still handles those proposals, not that a live model will always regenerate them.
Pytest and the Docker test profile force mock mode and clear live credentials. GitHub Actions runs
offline and SQL Server suites without Azure credentials. `scripts.evaluate` also retains the original
27-question mock score and 50-attack corpus.

For authorized live reevaluation, use the command and quota guidance in [the live runbook](LIVE_AZURE_OPENAI.md).
Keep the UI idle during batches. Output paths must be new, and the local-only harness refuses cloud SQL
hosts. An Azure SQL deployment needs a separately authorized acceptance run and actual identity tests.

## Mandatory security and learning gates

Tests cover unauthorized schema/columns, cross-database/system/external access, DML/DDL/procedures,
unsafe functions, hints, batch injection, recursive queries, join fanout and ranked-join bypasses.
Additional attacks run through both the gateway and `/practice`. Real database tests deliberately
bypass the application validator and confirm that SQL Server itself denies base/internal reads, writes
and object creation. Actual lock/driver timeout, row/byte bounds, concurrency, signed Entra claims,
spoofed headers, conversation ownership and parameter injection are also tested.

Learning Mode is permanent: SQL display, construct explanations, 27 independent practice references,
alternative-query evaluation and reference verification remain available. Arbitrary live questions have
lessons but do not get a fabricated practice oracle. Candidate numbers are compared exactly; reference
ORDER BY must be honored. Permission checks are identical to the production question path.
