# Milestones and production-readiness gaps

| Milestone | Implemented/prepared | Remaining |
|---|---|---|
| M1 | Five tables, deterministic seed, views, runtime DENY, FastAPI, Responses adapter/mock, SQL policy, Streamlit, lessons, practice, tests, Linux containers and CI | Live Azure model behavior intentionally unmeasured |
| M2 | Entra JWT validator, strict cloud settings, managed identity connection adapters, private Bicep templates, deployment runbook | Approved resources, actual model deployment, delegated cloud frontend, registry access, private user networking, live identity verification and telemetry/alerts |
| M3 | Backend protocol and disabled Fabric adapter, ingestion specification, dialect checklist, DAX definitions and report design | Approved separate Lakehouse/pipeline, curated tables, endpoint capability tests, verified semantic model/report |
| M4 | Threat model, bounded queries, audit event skeleton, denial corpus and correctness tests | Row-level security, end-user identity propagation, distributed limits, durable tamper-resistant audit, red-team review, governance, SBOM/dependency scanning, backup/restore and incident exercises |

No claim of unrestricted NL-to-SQL correctness, general SQL equivalence, privacy against statistical
inference or production readiness is made. Local mode trusts the workstation operator. SQL validity
does not prove a business answer. Practice fixtures are fixed to the shipped seed. Unsupported SQL is
rejected even when harmless. The mock recognizes the exact example wording after simple case and final
punctuation normalization; new phrasing is a live-model evaluation task.

Azure templates have no deployed verification. Fabric deliberately fails closed. The M1 frontend is
not a cloud authentication gateway. SQL timeout tests establish actual cancellation/lock behavior on
the tested local driver/server combination; repeat them for Azure SQL and each Fabric endpoint.

Local live-inference preparation now includes the explicit Docker override, normalized endpoints,
sanitized provider diagnostics, bounded owner-scoped conversation memory and a ranked-invoice join
whose cardinality is checked by the gateway. See [the live runbook](../LIVE_AZURE_OPENAI.md). These
changes do not remove the M2 cloud-hosting, real identity or live-model evaluation gates. Conversation
memory is single-process and expires; durable/distributed history is future work.
