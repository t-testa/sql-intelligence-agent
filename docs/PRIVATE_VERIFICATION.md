# Private deployment verification — October 8, 2026

Later update: [portable deployment verification](PORTABILITY_VERIFICATION.md) records the new
Windows/WSL launchers, 466 passing tests per platform and the temporary Azure lifecycle plan.
The historical results below remain the earlier private-access baseline.

**Local changes validated. Not yet ready to request Azure provisioning approval.**
The full source is subject to the PRIVATE-only policy. The owner subsequently supplied
`https://github.com/t-testa/sql-intelligence-agent` and authorized a push after the source/history audit.
GitHub API metadata confirms **private** visibility and Pages disabled. See the
[source publication audit](GITHUB_PUBLICATION.md). No showcase was created and no user, collaborator
or Azure permission was granted.

**Owner-approval follow-up:** the supplied tenant and sole user object ID are now configured in ignored
local files and matching API/frontend authorization parameters. Both templates use the explicit tenant.
The targeted authentication suite passes **87/87**. An offline check using the saved configuration
confirms one user, owner acceptance when enabled only in test memory, rejection of other users/tenants,
anonymous/app-only/expired tokens, and access disabled in the saved cloud configuration. Both changed
templates compile. Evidence: `artifacts/owner-authorization-tests.xml` and
`artifacts/owner-authorization-verification.json`. This did not create an Azure assignment or validate
a real Entra login. Registration/callback configuration remains incomplete; the later repository URL
has been recorded separately in the ignored preflight configuration. Other local settings and existing
secrets were preserved.

## Completed changes

- Streamlit delegates browser sign-in to ACA Easy Auth and forwards only its delegated API access token.
  Cloud configuration requires a fixed HTTPS API origin and rejects the shared local token. No token
  is stored in Streamlit session state or sent through redirects.
- FastAPI independently verifies signature, issuer/tenant, audience/time, sole approved user, delegated
  scope, v2 token version and approved frontend client. Duplicate bearer headers, forged signatures,
  identity-header spoofing, app-only and wrong-user/client tokens fail before SQL or model calls.
- Authentication failures clear conversation/results/practice state and stop subsequent operations
  pending full sign-in. A late 403 receives one failed request without an automatic analytical retry.
  The deployment's API access switch defaults off. Cloud OpenAPI/docs are disabled; minimal liveness
  has no database/model capability.
- Private templates now include an internal ACA environment with public networking disabled, separate
  identities, private SQL/token store, endpoint NSG and private DNS, authenticated ACR and Easy Auth.
  Existing OpenAI is reused. No account/model or role-assignment resource is created by the templates.
- The read-only preflight checks approved identity inputs and, when available, actual tenant/application/
  assignment/consent metadata and GitHub privacy. Unknown values fail closed. CI refuses a public
  source repository; it cannot prevent an owner manually changing visibility.
- The private plan separates app and GitHub grant/revoke procedures, costs, credential rotation,
  private routing, cloud acceptance and cleanup. A private showcase content plan exists; no showcase,
  export bundle or demo video has been created or published.

## Actual verification

| Check | Outcome |
|---|---|
| Full Windows regression | **443/443**, 0 failed/errors/skipped; 7.73 seconds |
| Full Linux Docker regression | **443/443**, 0 failed/errors/skipped; 5.47 seconds |
| Mandatory local security directory | **198/198 on each platform** |
| Actual SQL runtime permission denials | **6/6 on each platform**, bypassing application validation |
| Recorded live corpus replay | **61/61**, no model calls |
| Independent reference SQL/fixture comparison | **53/53** |
| Mock catalog / adversarial policy corpus | **27/27 / 50/50 rejected** |
| Added private-access coverage | **76 tests**, preserving the previous 367 and original 218 baseline |
| Ruff / formatting / strict mypy | Pass; 61 Python files formatted, 36 typed source files |
| Foundation, API, frontend Bicep | All compile; not applied |
| Compiled private-template checks | Internal/public-disabled environment, access-off default, one user, Easy Auth and secure parameters confirmed |
| Publication secret audit | Candidate files and full Git history scanned with Gitleaks; separate configured-secret/object checks; see [audit](GITHUB_PUBLICATION.md) |
| Rebuilt local app | Healthy API/UI/SQL; live catalog loads and Learning Mode remains enabled |
| New billable inference during this private-access change | **None** |

Evidence: ignored `artifacts/private-windows.xml`, `artifacts/private-linux.xml`,
`artifacts/private-preflight.json`, `artifacts/private-audit.json`, compiled `artifacts/private-*.json`; source tests in
`tests/security/test_private_access.py` and `test_private_preflight.py`. Tests use locally signed RSA
tokens and mocked HTTP for Entra flows. UI tests include absent token, expired token, HTML 401, late
403, state clearing and no analytical retry. They do **not** prove that a real tenant or Easy Auth
sidecar is configured correctly. One upstream Starlette/AnyIO deprecation warning remains.

The earlier real Azure run remains **61/61 on the finite supported set** (53 queries, 8 clarification/
refusal outcomes), from `sql-agent-model`. See [the live report](RELEASE_VERIFICATION.md) for actual
model receipts, initial 35/61 result, investigated failures and full retests. No expected outputs,
SQL gateway rules, model prompt, tool contract or Learning Mode exercises changed in this private-access
work. The frozen corpus hash is unchanged:
`a0d9d4c0920c7cc6047bf1dc7a9ccf85d3d4251940e24e8fe3994a571e46cc1b`.
There is no claim of universal SQL correctness, zero hallucinations or cloud production certification.

## Blocking gates and next evidence

1. **Owner identity approved; registration setup pending:** the user explicitly supplied the tenant
   and sole user object ID. Both are saved in ignored private configuration and matching API/frontend
   partial parameters; the local Entra allowlist has exactly one user. Cloud access stays disabled.
   Registration IDs, exact private callback, actual enterprise assignments and delegated consent still
   require completion. No Azure assignment or tenant mutation was made by recording these identifiers.
2. **GitHub privacy verified:** the owner-created repository is private, Pages is disabled and the
   existing Git credential has push access. The owner authorized the audited private push. This closes
   the repository-identification/visibility blocker; no visibility or collaborator changes are authorized.
3. **Private route/callback and cost quote are incomplete:** identify approved VPN/workstation/DNS,
   migration subnet, image-build path, SAS/OAuth rotation operator and reuse inventory. The $40–80/month
   application subtotal excludes private user connectivity; it is not an approved total budget.
4. **Cloud identity and predeployment checks must finish before a provisioning request:** complete
   metadata checks, exact parameters, private network design, cost estimate and reviewed what-if.
   The current preflight returns blocked as intended. No provisioning approval is requested now.
5. **Actual platform acceptance is pending:** after separately approved private provisioning, verify
   real login/renewal/logout/revocation, private DNS/TLS/NSGs, MI and SQL DENY, reference/replay/live
   accuracy, Learning Mode, alert delivery and credential rotation before enabling use.

The token store uses a short-lived user-delegation SAS under the stable ACA auth API; rotation and
private sidecar connectivity must be operationally proven. Existing OpenAI public/key access is not
changed by merely adding a private endpoint; review consumers and obtain explicit cutover approval.
Keep API access disabled on failed acceptance. A logout or Entra assignment removal does not instantly
invalidate all issued JWTs; the API allowlist/kill switch plus old-revision deactivation is the independent
revocation boundary. Source access can be revoked separately but prior clones cannot be erased.

Use [the private Azure plan](AZURE_RELEASE_PLAN.md), [Entra runbook](PRIVATE_AUTH.md) and
[private showcase content plan](PUBLIC_SHOWCASE_APPROVAL.md) for the next approved steps.
