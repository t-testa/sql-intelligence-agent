# Milestones and production-readiness gaps

The two-mode [portability report](PORTABILITY_VERIFICATION.md) records verified Windows/WSL local
operation and 466 passing tests on each platform. Private Azure remains unprovisioned; follow the
[temporary Azure lifecycle runbook](AZURE_LAB_RUNBOOK.md) for remaining gates and cleanup.

| Milestone | Implemented/prepared | Remaining |
|---|---|---|
| M1 | Five tables, deterministic seed, views, runtime DENY, FastAPI, live Responses adapter/mock, SQL policy, Streamlit, permanent lessons/practice, recorded live corpus, tests and CI | Finite measured corpus, no universal correctness claim; see release verification |
| M2 | Existing model verified live; delegated frontend adapter, independent Entra API checks, explicit sole-owner tenant/user configuration, private GitHub visibility verified, private templates and read-only preflight | Registration/callback setup, route/DNS/cost review, actual platform/MI/SQL acceptance and tested alerts |
| M3 | Backend protocol and disabled Fabric adapter, ingestion specification, dialect checklist, DAX definitions and report design | Approved separate Lakehouse/pipeline, curated tables, endpoint capability tests, verified semantic model/report |
| M4 | Threat model, bounded queries, audit event skeleton, denial corpus and correctness tests | Row-level security, end-user identity propagation, distributed limits, durable tamper-resistant audit, red-team review, governance, SBOM/dependency scanning, backup/restore and incident exercises |

No claim of unrestricted NL-to-SQL correctness, general SQL equivalence, privacy against statistical
inference or production readiness is made. Local mode trusts the workstation operator. SQL validity
does not prove a business answer. Practice fixtures are fixed to the shipped seed. Unsupported SQL is
rejected even when harmless. The mock recognizes the exact example wording after simple case and final
punctuation normalization; new phrasing is a live-model evaluation task.

Azure templates have no deployed verification. Fabric deliberately fails closed. The cloud frontend
delegates sign-in to Easy Auth while FastAPI remains the independent authorization boundary.
SQL timeout tests establish actual cancellation/lock behavior on
the tested local driver/server combination; repeat them for Azure SQL and each Fabric endpoint.

Local live-inference preparation now includes the explicit Docker override, normalized endpoints,
sanitized provider diagnostics, bounded owner-scoped conversation memory and a ranked-invoice join
whose cardinality is checked by the gateway. See [the live runbook](../LIVE_AZURE_OPENAI.md). These
changes do not remove the M2 cloud-hosting and real identity gates. Actual live model results are in
[release verification](RELEASE_VERIFICATION.md). Conversation
memory is single-process and expires; durable/distributed history is future work.

GitHub API metadata confirms the full source repository `t-testa/sql-intelligence-agent` is PRIVATE
and Pages is disabled. See the [source audit](GITHUB_PUBLICATION.md). Public source/application deployment
is not planned. Only a separately approved sanitized showcase may become public.
See [current private verification](PRIVATE_VERIFICATION.md).
