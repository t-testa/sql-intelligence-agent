# Private Azure templates — preparation only

No template has been applied. Follow the [private plan](../docs/AZURE_RELEASE_PLAN.md) and
[actual October 8 preflight](../docs/AZURE_PREFLIGHT_2026-10-08.md). Entra owner-only preparation is
complete; the billable topology/callback sequence awaits the explicitly requested exception.

- `main.bicep`: internal ACA/public network disabled; private SQL Basic, endpoint NSG/DNS, separate
  API/frontend MI, authenticated ACR Basic, private token storage, logs and insights. Reuses OpenAI;
  creates no new model/account or role assignments.
- `private_dns.bicep`: second stage using the foundation's generated environment domain/private IP;
  creates private wildcard/apex DNS and the application VNet link. Owner route/forwarding remains explicit.
- `application.bicep`: private Entra API, runtime MI, strict inference limits, one replica and API
  access **disabled by default**. Initially accepts exactly one approved user object ID.
- `frontend.bicep`: private-network Streamlit, owner-only Easy Auth and delegated API scope/token store.
  `enablePrivateIngress=false` on the first deployment prevents ingress before auth is installed.
  Must target the verified internal environment. Its external ingress must never face an external ACA
  environment. FastAPI independently verifies every forwarded access JWT.
- Parameter examples are placeholders, not approved identities or deployment targets.
- `lab.bicep`: subscription wrapper for a what-if against a new group without creating the group first.
  Optional operator host defaults off. Do not deploy disposable what-if password inputs.
- `operator.bicep`: separately approved temporary Windows D2as v4 VM, Standard SSD/outbound IP,
  private RDP NSG and free Bastion Developer; its additional charges are in the preflight quote.

The foundation requires the approved tenant and migration-admin principal type (`User` by default).
`createValidationDatabase` defaults false; the full Azure acceptance plan explicitly enables the second
synthetic database and includes its cost. Complete API/frontend parameter examples and a separate cloud
runtime env example are provided. Keep populated copies ignored under `.local/`.
See [the temporary lab runbook](../docs/AZURE_LAB_RUNBOOK.md); no command has provisioned these resources.

The approved initial tenant and sole user are stored only in ignored `.local/` configuration. Its
API/frontend `*.authorization.parameters.json` files are partial inputs, not deployment commands.
Both templates require the explicit `entraTenantId`; do not infer it from the CLI operator. Cloud
API access stays disabled until the remaining identity/network/release gates pass.

Compile using [DEPLOYMENT.md](../DEPLOYMENT.md). Compilation does not prove private routing, login,
consent, effective permissions, regional availability or Azure SQL accuracy. Read-only preflight
rejects reused public environments. Images must use immutable digests and private registry identity.

After the cost/sequence approval, narrow grants remain necessary: runtime OpenAI User on the existing model resource,
AcrPull for both container identities, a contained read-only SQL user, and a scoped token-store SAS
rotation identity. No hidden role-assignment resources are included. SQL bootstrap, Entra registration/
consent read-back, private browser DNS/routing and alerts remain reviewed gates. The metadata checks
passed for the created owner-only registrations; actual platform login remains unexecuted.

Existing OpenAI public/key-auth properties are not changed by this foundation; review the private
cutover separately. Storage denies shared-key/public access, so the private token-store SAS must be a
user-delegation SAS. Rotate before its delegation key expires. Both SAS and OAuth client secrets are
secure parameters stored as ACA secrets, not container environment variables or outputs.

Schemas were checked against Microsoft references for
[ACA](https://learn.microsoft.com/en-us/azure/templates/microsoft.app/2025-07-01/managedenvironments),
[authentication](https://learn.microsoft.com/en-us/azure/templates/microsoft.app/2025-07-01/containerapps/authconfigs),
[SQL](https://learn.microsoft.com/en-us/azure/templates/microsoft.sql/2023-08-01/servers) and
[ACR](https://learn.microsoft.com/en-us/azure/templates/microsoft.containerregistry/2025-04-01/registries).
