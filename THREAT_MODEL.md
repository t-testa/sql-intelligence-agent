# Threat model

Assets: database integrity, approved data confidentiality, Azure credentials, compute budget, user
identity and analytical correctness. Untrusted inputs: questions, SQL proposals, bindings, JWTs,
retrieved text and practice submissions. Trusted components: deployed code/catalog, reviewed views,
configured identities and migration artifacts.

| Threat | Control | Evidence / remaining gap |
|---|---|---|
| Direct SQL injection | AST policy + separate ODBC binding + database DENY | Bound attack string returns zero rows; no writes |
| Prompt injection | No execution tool; validate every proposal; no results sent to model | Malicious mocked proposals cannot reach executor |
| Base/internal data access | Source and scoped-column allowlists; object grants only | Policy and real database denial tests |
| Privilege escalation | Separate bootstrap identity; startup permission checks | Runtime is neither sysadmin nor db_owner |
| Fanout and wrong totals | Job-grain views; reviewed join direction; independent oracle | Raw join deliberately demonstrates 3× / 2× inflation |
| Availability/cost attack | Grammar/complexity caps, concurrency, driver deadline, lock timeout, bounds | Real lock cancellation, row and payload tests; no distributed request budget yet |
| Spoofed identity | Verify signed Entra JWT and allowlisted oid/scope | Offline signed-token tests; live tenant flow pending M2 |
| Data exfiltration via functions | Positive function/node set; deny external sources and procedures | 50-attempt rejection corpus; novel attacks still require review |
| Output injection | Deterministic summaries; plain-text UI; no model feedback loop | Retrieved instruction test; no HTML execution |
| Secret/log leak | Ignored .env; runtime excludes admin credentials; sanitized errors and audit hashes | Local developer filesystem remains trusted |
| Wrong but safe model query | Inspectable SQL, clarification, independent fixtures | Mock benchmark is not a claim of live model accuracy |
| Cross-user leakage | Private local profile; delegated tokens and owner/client allowlists in cloud | Offline isolation/expiry/revocation tests pass; actual tenant flow remains M2; row-level scopes remain M4 |
| Public source or endpoint exposure | PRIVATE repository policy, CI privacy guard, internal ACA/private SQL, independent API authorization | Remote visibility and private route still require verification; showcase creation/publication needs separate content approval |
| Supply-chain regression | Exact dependency locks, pinned parser, CI | Lock updates require review; vulnerability scan/SBOM remains a readiness task |

The privileged test process is not a production service. Its direct base-table queries exist only to
establish reference truth. Do not give these credentials to the agent or expose bootstrap scripts as tools.

Residual risk: broad approved datasets can reveal business patterns, a single large scalar can allocate
driver memory before application bounds apply, and timeouts do not provide resource governance. The
local API token identifies one operator, not individual people. Monitoring infrastructure alone does
not make logs durable or prove detection coverage.
