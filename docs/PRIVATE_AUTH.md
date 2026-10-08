# Entra configuration and private acceptance runbook

Status: adapter and offline security tests implemented; actual tenant configuration and platform
sign-in **not verified**. Do not request billable provisioning approval until the identity and
predeployment checks below are complete. No tenant changes or access grants have been made.

The owner has now explicitly approved the sole initial tenant/user. Those exact identifiers are saved
in ignored `.local/private-preflight.json`, `.local/cloud-authorization.env`, and the two partial
`.local/*.authorization.parameters.json` files, as well as the local `.env` Entra settings. The API and
frontend templates require the same explicit `entraTenantId`; they no longer infer it from the operator.
Examples and source files retain placeholders. Registration IDs and private callback are still unset;
cloud API access remains disabled. Saving this configuration did not create an Entra assignment.

## Required approved values

Obtain the tenant ID and **user object ID in that tenant** explicitly approved by the owner. Do not
use an email string as the API allowlist value; do not infer approval from CLI/GitHub login. Initially
there is exactly one user. Also identify the approved API/frontend registration IDs, SQL migration
administrator, private user route, target subscription/group and private GitHub repository. Keep these private.

Create registrations/credentials/consents/assignments only after the owner approves those exact changes.
Use existing compatible registrations where practical. No subscriptions roles are needed by app users.

| Setting | API registration | Frontend registration |
|---|---|---|
| Accounts | Single tenant (`AzureADMyOrg`) | Same single tenant |
| Client ID | Separate API UUID | Separate frontend UUID |
| Token version | `api.requestedAccessTokenVersion=2` | Easy Auth OIDC configuration |
| Exposed scope | `api://API_CLIENT_ID/access_as_user`, delegated, enabled | Delegated permission to that API scope |
| Web callback | None required for API | Exact approved `https://PRIVATE_HOST/.auth/login/aad/callback` |
| Public client/SPA flows | Disabled | Disabled; no SPA or mobile redirect |
| ID token issuance | Not used as API authorization | Enable for Easy Auth support |
| Implicit access-token issuance | Disabled | Disabled |
| Enterprise app assignment | Required; only approved user | Required; only approved user |

After approval, grant only the required delegated consent. Do not add an app-only query role or a
Graph permission merely to log in. ID-token issuance for frontend sign-in is required by
[Easy Auth](https://learn.microsoft.com/en-us/azure/container-apps/authentication); it does not make an
ID token valid for FastAPI. Azure app registration details are described in
[Microsoft's Entra setup](https://learn.microsoft.com/en-us/azure/container-apps/authentication-entra).

Private hostname selection is a predeployment dependency. Prefer an approved stable private name
whose DNS/certificate plan is known. If only a newly generated ACA hostname is available, the exact
callback cannot be verified yet; keep that gate explicitly blocked rather than inventing a URI or
claiming cloud authentication complete. Do not add wildcard, public-demo or unreviewed callbacks.

## Runtime configuration

FastAPI: `APP_ENV=cloud`, `AUTH_MODE=entra`, `ENTRA_TENANT_ID=<tenant UUID>`,
`ENTRA_AUDIENCE=<API client UUID>`, `ENTRA_FRONTEND_CLIENT_ID=<frontend UUID>`,
`ENTRA_ALLOWED_OBJECT_IDS=["<approved user UUID>"]`, `ENTRA_REQUIRED_SCOPE=access_as_user`.
The v2 API audience is the client UUID, not the `api://` scope URI. Start with
`APPLICATION_ACCESS_ENABLED=false`; enabling private acceptance calls requires the approved owner
and completed access configuration. Runtime SQL uses MI and certificate verification; OpenAI uses
runtime MI, never an API key. Preserve all existing SQL/inference bounds.

Streamlit: `APP_ENV=cloud`, `API_URL=https://<private API FQDN>`. No `LOCAL_API_TOKEN`, SQL credentials,
OpenAI keys or token-bearing URL. Launch with `python -m streamlit run frontend/app.py` to preserve
package imports. Keep CORS/XSRF protection enabled. Easy Auth requires login on all application paths,
HTTPS, validated nonce, sole-user object-ID restriction and no external redirect allowlist.

Configure Easy Auth's frontend client ID, issuer `https://login.microsoftonline.com/TENANT_ID/v2.0`,
client-secret reference and login parameter:

```text
scope=openid profile offline_access api://API_CLIENT_ID/access_as_user
```

Enable the token store using a private Blob container. The supplied stable template stores the OAuth
secret and token-container user-delegation SAS as ACA secrets, without exposing them as container env
variables or outputs. A delegation key lasts at most seven days; define a scoped rotation operator and
expiry alerts before deployment. Confirm sidecar connectivity to the private blob endpoint and rotation
in the actual environment. Microsoft documents [delegation SAS expiry](https://learn.microsoft.com/en-us/rest/api/storageservices/create-user-delegation-sas).

## Independent API boundary and session behavior

Streamlit forwards exactly one `X-MS-TOKEN-AAD-ACCESS-TOKEN` from the initial websocket headers as
Bearer to the configured HTTPS API, without redirects. It never authorizes based on a name/header
claim. FastAPI checks signature/issuer/audience/lifetime plus `tid`, `oid`, `scp`, `ver=2.0` and the
approved `azp` on each protected request. Expired, wrong-audience/client/user/tenant, app-only and forged
tokens fail before inference or SQL. Duplicate bearer headers fail. `/health` is the only intentional
unauthenticated API operation: fixed liveness, no data/model/database access. API docs/schema are off.

Tokens are not retained in Streamlit session state, query strings or logs. A missing token or API
401/403 clears displayed history, conversation ID and practice state. The user follows **Sign in
again** for full navigation and a fresh authenticated websocket. Streamlit reruns do not refresh the
initial handshake headers. Test this real flow; do not automatically retry a failed analytical request.
See [Streamlit context semantics](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.context).

**Sign out** uses `/.auth/logout`; close old tabs/websockets as part of logout acceptance. An already
issued access token may remain cryptographically valid until expiry. Logout alone is not immediate
API revocation. Remove the user from the API allowlist (or disable all application access), roll out
the new revision, deactivate old revisions, remove enterprise/Easy Auth assignments and verify that
the old JWT is denied. The app and source repository are revoked independently.

## Read-only preflight and actual cloud acceptance

1. Copy `infrastructure/private-preflight.example.json` to ignored `.local/private-preflight.json`.
   Populate only approved values, including the exact private callback and `owner/repository`.
2. Run `python -m scripts.private_preflight --read-cloud` using the approved tenant's existing CLI
   login. It reads application/SP metadata, enabled user, sole-owner assignments, API consent,
   callback/scope/version and GitHub visibility. It never logs in or grants access. If CLI read access
   is unavailable, retain equivalent connected-tool evidence; a failed check is not silently waived.
3. Verify separate manual predeployment gates: private route/DNS, approved subnet plan, credential
   rotation, selected immutable images, reuse inventory, price quote and reviewed template what-if.
   Only after these and identity checks pass may provisioning approval be requested.
4. After approved private provisioning, test real allowed-user login and token handoff; no token values
   in screenshots/logs. Confirm a correct question and Learning Mode through FastAPI, and no provider
   calls for rejected users/requests. Negative tests include anonymous direct API access, forged headers,
   wrong audience/client/scope/tenant, expired token and revoked owner. Use offline synthetic tokens for
   most cases; do not create or invite an additional tenant user just for a negative test.
5. Test refresh/full navigation, logout/new tabs, credential expiry/rotation, private DNS, TLS, MI renewal,
   SQL direct denials, timeout/overflow, independent references/replay and approved live accuracy.
   Verify the API and SQL cannot be reached through public ingress or the browser subnet.
6. Preserve sanitized outcome counts in a private report. Leave access disabled if a mandatory gate fails.

Metadata checks and locally signed JWT tests are not actual cloud sign-in validation. The current
preflight still blocks on registration/callback values; owner approval and the private repository are recorded.
No provisioning request is being made.
