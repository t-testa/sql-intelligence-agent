# Private Azure templates — preparation only

No template has been applied. Follow the [private plan](../docs/AZURE_RELEASE_PLAN.md) and
[Entra runbook](../docs/PRIVATE_AUTH.md). All billable changes and access grants need approval.

- `main.bicep`: internal ACA/public network disabled; private SQL Basic, endpoint NSG/DNS, separate
  API/frontend MI, authenticated ACR Basic, private token storage, logs and insights. Reuses OpenAI;
  creates no new model/account or role assignments.
- `application.bicep`: private Entra API, runtime MI, strict inference limits, one replica and API
  access **disabled by default**. Initially accepts exactly one approved user object ID.
- `frontend.bicep`: private-network Streamlit, owner-only Easy Auth and delegated API scope/token store.
  Must target the verified internal environment. Its external ingress must never face an external ACA
  environment. FastAPI independently verifies every forwarded access JWT.
- Parameter examples are placeholders, not approved identities or deployment targets.

The approved initial tenant and sole user are stored only in ignored `.local/` configuration. Its
API/frontend `*.authorization.parameters.json` files are partial inputs, not deployment commands.
Both templates require the explicit `entraTenantId`; do not infer it from the CLI operator. Cloud
API access stays disabled until the remaining identity/network/release gates pass.

Compile using [DEPLOYMENT.md](../DEPLOYMENT.md). Compilation does not prove private routing, login,
consent, effective permissions, regional availability or Azure SQL accuracy. Read-only preflight
rejects reused public environments. Images must use immutable digests and private registry identity.

After approval, narrow grants remain necessary: runtime OpenAI User on the existing model resource,
AcrPull for both container identities, a contained read-only SQL user, and a scoped token-store SAS
rotation identity. No hidden role-assignment resources are included. SQL bootstrap, Entra registration/
consent, private browser DNS/routing and alerts remain separate reviewed gates.

Existing OpenAI public/key-auth properties are not changed by this foundation; review the private
cutover separately. Storage denies shared-key/public access, so the private token-store SAS must be a
user-delegation SAS. Rotate before its delegation key expires. Both SAS and OAuth client secrets are
secure parameters stored as ACA secrets, not container environment variables or outputs.

Schemas were checked against Microsoft references for
[ACA](https://learn.microsoft.com/en-us/azure/templates/microsoft.app/2025-07-01/managedenvironments),
[authentication](https://learn.microsoft.com/en-us/azure/templates/microsoft.app/2025-07-01/containerapps/authconfigs),
[SQL](https://learn.microsoft.com/en-us/azure/templates/microsoft.sql/2023-08-01/servers) and
[ACR](https://learn.microsoft.com/en-us/azure/templates/microsoft.containerregistry/2025-04-01/registries).
