# Temporary private Azure deployment and teardown

This is the reproducible execution plan, **not evidence of an Azure deployment**. No new resource,
identity grant or public endpoint is approved by this document. Complete identity/predeployment checks
before requesting approval for a named resource inventory, short operating window and spending limit.
Keep the full GitHub repository private. SQL Learning Mode and the existing validation/security gateway
are required in both operating modes. See [local operations](LOCAL_PORTABLE.md) for the independent fallback.

## 1. Preserve the redeployment inputs and define the boundary

Use a dedicated application resource group, provisionally `sqlintel-lab`, with a recorded subscription,
tenant, location, prefix and expiry date. Never put the existing OpenAI account in that group or move it
there. Privately record its full resource ID, deployment `sql-agent-model`, existing network/auth
settings and any shared consumers. The foundation declares it `existing` and creates no new model.

Preserve outside the group: private Git commit, lockfiles, Docker image digest, frozen corpus/recording
hashes, synthetic seed, runbooks, sanitized reports and encrypted private configuration/credentials.
The local `.env` must remain a separate configuration from `.local/cloud-runtime.env` and cloud ARM
parameters. No cloud cleanup command touches local Docker volumes or files.

Create an ignored `.local/azure-lab-ledger.json` before any approved mutation, recording:

| Record | Purpose |
|---|---|
| Subscription/tenant; exact application group ID | Prevent wrong-subscription/group operations |
| Protected OpenAI ID and its separate group | Hard exclusion from deletion |
| Resource inventory and expiry/budget owner | Review every billable item, including connectivity |
| Preexisting vs newly created Entra applications, SPs, credentials and assignments | Remove only lab-owned identity objects |
| Exact role-assignment IDs and scopes, private endpoint connection IDs | Clean up cross-group leftovers without removing shared grants |
| Client/migration VNets, peerings, DNS links and certificates | Review resources outside the dedicated group |
| Previous image digests/revision names and access settings | Safe rollback |
| Evidence directory and encrypted backup location | Survive deletion |

No secrets belong in this ledger. Store OAuth/SAS credentials in a private secret store or encrypted
owner backup; inject them through ignored ARM parameter files with `@secure` template parameters.

## 2. Complete identity, private access and cost preflight

Use the already approved sole owner and tenant from ignored private configuration. Finish
[PRIVATE_AUTH.md](PRIVATE_AUTH.md): two single-tenant registrations, exact delegated scope/audience,
approved frontend client, owner-only assignments and consent, and an exact private HTTPS callback.
Creating registrations, credentials or grants still needs explicit approval. SQL migration admin is a
separate privileged role: explicitly approve the owner for it; do not invent a group or grant anyone else.
The foundation now accepts `User` (default) or an explicitly approved `Group`, and an explicit tenant.

Choose a stable private frontend hostname and its DNS/TLS certificate plan before approval. The default
ACA hostname is generated only after its environment exists. It cannot satisfy the earlier exact-callback
gate in advance. Reuse an existing verified internal environment, or prepare an owner-approved stable
private hostname/certificate and custom-domain binding. **A missing route, hostname or certificate is a
blocker, not permission to expose public ingress.** The current frontend template uses the generated ACA
hostname; a stable custom binding must be supplied and reviewed before using that alternative.

Select an existing approved VPN/connected workstation/private route where possible. Confirm no overlap
with `10.48.0.0/16`; the current application subnet is `10.48.0.0/23`, endpoint subnet `10.48.2.0/24`.
Specify a distinct approved migration subnet. Only that subnet and app infrastructure may reach SQL;
browser subnet access to SQL/token storage remains denied. Plan private DNS forwarding for owner and
migration clients, not just VNet links. New VPN/resolver/VM costs need a separate explicit quote.

Cloud inference must resolve the reused OpenAI hostname through its private endpoint. Preserve an
approved authenticated local access path to that same account independently of the lab group. Do not
disable existing key/network access as a blanket cutover. Any narrower firewall change needs a before/
after consumer test and explicit approval. If the owner chooses private-only model access, retain and
price a private local route outside the disposable group; otherwise deletion can break local inference.

```powershell
# Existing approved CLI login; no login/grants/deployment are performed by this helper.
.\.venv\Scripts\python.exe -m scripts.private_preflight --read-cloud
az bicep build --file infrastructure/main.bicep --outfile artifacts/lab-foundation.json
az bicep build --file infrastructure/private_dns.bicep --outfile artifacts/lab-dns.json
az bicep build --file infrastructure/application.bicep --outfile artifacts/lab-api.json
az bicep build --file infrastructure/frontend.bicep --outfile artifacts/lab-frontend.json
.\local.cmd test
```

Capture CLI/Docker/Python/Bicep versions, current private GitHub visibility, exact commit, dependency
audit/image scan, parameter review and cost quote. A compiler pass is not a deployment or identity test.
Before approval, copy parameter examples into ignored `.local/`; fill placeholders without printing
secure parameters. The complete 61-case cloud acceptance requires `createValidationDatabase=true`
for the edge fixture. This adds a second temporary SQL Basic database to the billable inventory.

Use the dated prices in [the release plan](AZURE_RELEASE_PLAN.md), then refresh the quote before approval.
The earlier $40–80/month subtotal becomes roughly **$45–85/month with the second database**, still
excluding owner connectivity and any custom-domain/certificate costs. A three-day lab is not guaranteed
to cost exactly 3/30 of that figure: check meter minimums, active compute, traffic and log volume.
Local Compose has no application-hosting Azure charges; live questions still consume OpenAI tokens.

## 3. Provision only after explicit approval

The following commands are an operator sequence, not an automatic script. Every placeholder must resolve
to the reviewed inventory. Stop at the first failure; do not continue with partial identity/network state.
These examples run in PowerShell, with `$subscription`, `$tenant`, `$labGroup`, `$location` and
`$protectedOpenaiId` taken from the private ledger. Check the signed-in tenant/subscription first.

```powershell
az account show --query '{subscription:id,tenant:tenantId}' -o json
# Approval must cover this exact group and the resources in the reviewed what-if.
az group create --subscription $subscription --name $labGroup --location $location --output none
az deployment group what-if --subscription $subscription --resource-group $labGroup --template-file infrastructure/main.bicep --parameters '@.local/foundation.parameters.json'
az deployment group create --subscription $subscription --resource-group $labGroup --name foundation --template-file infrastructure/main.bicep --parameters '@.local/foundation.parameters.json' --output none
$foundation = az deployment group show --subscription $subscription --resource-group $labGroup --name foundation --query properties.outputs -o json | ConvertFrom-Json
az deployment group create --subscription $subscription --resource-group $labGroup --name private-dns --template-file infrastructure/private_dns.bicep --parameters environmentDefaultDomain=$($foundation.environmentDefaultDomain.value) environmentStaticIp=$($foundation.environmentStaticIp.value) applicationVnetId=$($foundation.applicationVnetId.value) --output none
```

For a new group, the group itself contains no billable workload; a resource-group what-if requires it
to exist. Review the compiled resource inventory before approval, then review this final what-if before
the first billable deployment. Provider registration, route/peering and existing-resource endpoint
approval are separate reviewed actions, not silently performed by these helpers.

Foundation resources: internal ACA environment, two user-assigned identities, VNet/endpoint NSG,
private SQL server and baseline/optional edge databases, OpenAI/SQL/blob private endpoints and DNS,
private token storage, authenticated ACR Basic, Log Analytics and an Application Insights resource.
ACR Basic has an authenticated public registry endpoint, not a private network endpoint; source/images
remain private. Requiring private-link ACR would need a revised Premium quote and template review.
The Insights resource alone does not instrument Python requests; use the tested platform/audit sources
below and do not claim automatic distributed tracing.

The second DNS stage uses the generated environment domain and static private IP for wildcard/apex
records, following [Microsoft's internal DNS guidance](https://learn.microsoft.com/en-us/azure/container-apps/vnet-custom).
Separately configure the approved client route/forwarder and stable frontend binding, if selected.
Verify DNS from the actual browser host, migration host and API network; do not rely only on ARM flags.

After separately approved grants, give runtime MI **Cognitive Services OpenAI User** only at the existing
OpenAI resource scope. Give both MIs **AcrPull** only at this registry. Record each new assignment ID;
do not duplicate or later remove a preexisting shared assignment. The frontend gets no SQL/model role.
Use a reviewed least-privilege migration operator and scoped blob delegation/SAS rotation operator.
No application user needs Azure Contributor/Owner. Use principal IDs for Azure role assignments.

## 4. Seed private SQL, build and deploy immutable images

On the approved migration host with private SQL connectivity, ODBC Driver 18, pinned Python dependencies
and the approved operator's existing Azure CLI login:

```powershell
$sqlHost = $foundation.sqlServerFqdn.value
$runtimeClient = $foundation.runtimeClientId.value
# Omit --apply to validate inputs without connecting. Apply only after bootstrap/grant approval.
.\.venv\Scripts\python.exe -m scripts.azure_sql --host $sqlHost --tenant-id $tenant --runtime-client-id $runtimeClient --database SQLIntelligence --apply
.\.venv\Scripts\python.exe -m scripts.azure_sql --host $sqlHost --tenant-id $tenant --runtime-client-id $runtimeClient --database SQLIntelligenceValidation --apply
```

This helper refuses non-Azure hosts, other database names and nonempty databases. It does not create
billable databases. Schema, deterministic seed, views and runtime grants are one transaction; failure
rolls back. An existing database must be verified, never dropped or overwritten just to rerun bootstrap.
The SQL user uses the MI **client ID** for `CREATE USER ... WITH SID ... TYPE=E`, as required by the
[current Azure SQL syntax](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-user-transact-sql?view=sql-server-ver17#k-create-a-contained-database-user-from-a-microsoft-entra-principal-without-validation).
The runtime then receives the existing `reporting_reader` view grants and base-table/write/DDL DENYs.

Copy `infrastructure/cloud-runtime.env.example` to `.local/cloud-runtime.env` on the migration host.
Populate reviewed cloud IDs/hostnames; leave secrets empty. Verify every independent reference there:

```powershell
.\.venv\Scripts\python.exe -m scripts.release_eval --azure-sql --env-file .local/cloud-runtime.env --mode references --output artifacts/azure-references.json
```

This command uses the CLI-authenticated operator only for independently written reference SQL. It
makes no model calls. Cloud model/replay execution uses runtime MI instead. Do not set `APP_ENV=local`
to bypass cloud identity requirements. Every evidence output must have a new filename.

On the approved private build workstation, build from the recorded Git commit. The Docker context
excludes `.env`, `.local` and `artifacts`. Scan the image and source before pushing to the private registry:

```powershell
$registry = $foundation.registryName.value
$registryHost = $foundation.registryServer.value
$commit = git rev-parse HEAD
az acr login --name $registry --output none
docker build -t "${registryHost}/sql-intelligence-agent:${commit}" .
docker push "${registryHost}/sql-intelligence-agent:${commit}"
$digest = az acr repository show --name $registry --image "sql-intelligence-agent:${commit}" --query digest -o tsv
```

Fill `.local/api.parameters.json` and `.local/frontend.parameters.json` from their examples and foundation
outputs. Use the same `${registryHost}/sql-intelligence-agent@${digest}` for both, exact sole-owner IDs,
the existing model, the verified private callback, and **API access disabled**. Securely supply the OAuth
secret and short-lived user-delegation SAS only in the private frontend parameter file. Never print it.
Deploy API first, then fill the frontend's `apiFqdn` from its output and deploy frontend:

```powershell
az deployment group create --subscription $subscription --resource-group $labGroup --name api --template-file infrastructure/application.bicep --parameters '@.local/api.parameters.json' --output none
az deployment group create --subscription $subscription --resource-group $labGroup --name frontend --template-file infrastructure/frontend.bicep --parameters '@.local/frontend.parameters.json' --output none
```

The API checks its actual SQL identity at startup even while user access is disabled. Inspect only
sanitized revision/health outcomes. Never export token-store blobs, raw `/.auth/me`, headers or full
environment/secret listings. Keep one API process/replica, zero minimum replicas and all existing limits.

## 5. Actual cloud acceptance and evidence

Enable the sole owner's API access only for an explicitly approved acceptance window after private
network and identity checks pass. Set `applicationAccessEnabled=true` in the reviewed API parameter
file and redeploy it; default stays false in source. A failed mandatory gate means disable it again.

From an approved operator session, use `az containerapp exec --resource-group $labGroup --name
sql-intelligence-api --command /bin/sh` to run the following **inside the API container**, where runtime
MI is available. The image includes frozen evaluation evidence; output goes to `/tmp`:

```sh
python -m scripts.cloud_permissions
python -m scripts.release_eval --azure-sql --mode replay --recording evaluation/recordings/accepted.json --output /tmp/azure-replay.json
# Only within the explicitly approved model-call budget; no automatic retries:
python -m scripts.release_eval --azure-sql --mode live --allow-cloud-call --limit 61 --interval-seconds 12 --output /tmp/azure-live.json
```

Use a second invocation of `cloud_permissions` with `SQL_DATABASE=SQLIntelligenceValidation` to check
the edge database. Runtime permission checks include real denied base-table access and effective
view/write/DDL permissions; reference/recorded/live comparison never lets the model grade itself.
The direct evaluation helper is an operator tool, not an application endpoint. Its passing result
does not substitute for delegated Entra and frontend tests. Respect the provider quota/shared local
usage and stop on 429; the helper has a finite call/token budget. Never reset limits to force a pass.

Before the revision/group is removed, privately capture each JSON report from `/tmp` through the
operator terminal's output capture (only the named report), or an approved private evidence sink.
Verify valid JSON, all expected case IDs, timestamps, corpus/prompt/contract hashes, deployment/model
receipts, token counts, zero failures and matching image digest. Keep complete reports outside Azure;
capture/report transport failure is a failed evidence gate. Raw exec/login terminal transcripts can
contain sensitive metadata and must not enter Git or a showcase.

| Acceptance | Evidence required before marking Azure verified |
|---|---|
| Routing/TLS | Real owner browser reaches private frontend; API inaccessible from browser/public networks; SQL public disabled; approved migration path succeeds; browser-to-SQL fails |
| Identity | Actual sole-owner sign-in, delegated token handoff, audience/tenant/client/scope checks, refresh/relogin/logout and old-token revocation; no user added for testing |
| Anonymous/forged requests | Direct `/catalog`, `/questions`, `/practice` return 401/403 from an app-network client; header spoofing and local shared token fail; no SQL/model activity |
| Managed identities | API starts with correct SQL principal; both database permission checks pass; live model receipts use existing deployment; frontend has no SQL/model permission |
| Accuracy | 53/53 independent query references; complete 61/61 replay and 61/61 actual live cases, including edge fixture; no changed expected outputs or hidden truncation |
| End-to-end UI | Owner asks highest-invoice question, sees all 240 rows and generated SQL, uses an existing clarification/follow-up, sees Learning Mode explanation and an existing independent alternative-query comparison |
| Limits and failure paths | 429s/budgets, SQL cancellation/concurrency/overflow, inference outage and expired credentials fail visibly; no mock fallback or widened limits |
| Security and learning | Entire local security/Learning Mode suite passes; actual Azure role/network/identity checks pass; test platform-specific cancellation without production data |
| Monitoring | Demonstrated receipt of a test alert; private audit event and ACA/SQL/model metrics correlate with the test; no credentials/prompts/results in telemetry |
| Rollback/redeploy | Previous image digest restored with access disabled, then accepted; later rebuild from saved inputs and regenerate MI grants/SQL SID for new identities |

Record each row as PASS/FAIL/NOT RUN with UTC time, operator, evidence path and failure classification.
There is no universal SQL-correctness or zero-hallucination claim. Any critical/high defect, security
failure, live-case failure or missing cloud evidence blocks the validated Azure label.

## 6. Monitoring and operating window

Configure and explicitly approve an action group/contact, resource-group budget with 50/80/100% alerts,
and useful low-volume alerts: API revision unhealthy/restarts, SQL DTU/failed connections/deadlocks,
OpenAI 429s/token use, authentication failures and OAuth/SAS expiry. A budget alert does not stop spending.
The existing Log Analytics daily cap is not a complete Azure cost cap. Keep the lab short and record its
planned deletion date; private endpoints/SQL/registry/logs may cost money while apps scale to zero.

ACA console logs receive the existing sanitized `sia.audit` query/policy/execution events. Confirm their
delivery and correlate counts with platform metrics; API request timing/distributed traces are not
automatically supplied merely by creating Application Insights. Test notification delivery with an
approved reversible alert condition, not by generating a flood of model requests. Export only sanitized
counts/timestamps and the exact alert definitions needed for redeployment. Do not invent observed
latency, usage or availability numbers before measurement.

## 7. Rollback, then complete cleanup after approval

For failure, set `applicationAccessEnabled=false` and redeploy the API parameter file. Confirm old
tokens cannot query. Preserve evidence before replacing anything. Restore the last reviewed immutable
digest in both parameter files, redeploy, verify active revisions and deactivate stale API revisions.
Do not roll back to anonymous/local auth, public ingress, SQL admin runtime or relaxed query limits.
No schema changes are needed for ordinary image rollback. Never overwrite a nonempty fixture database.

Before deletion, run local launch/replay and an approved live smoke test, and verify the existing model
has an independent surviving local access path. Export all lab evidence and the ledger outside the
group; preserve encrypted configuration, owner-approved TLS materials and exact source/image versions.
Synthetic Azure SQL can be recreated from seed. Export wanted nonreproducible data explicitly before
deletion; no such customer data belongs in this project.

Deletion requires explicit approval for the inventory below. It is not implied by provisioning approval:

```powershell
az resource list --subscription $subscription --resource-group $labGroup --query '[].{id:id,type:type}' -o json
az lock list --subscription $subscription --resource-group $labGroup -o json
# Verify protectedOpenaiId belongs to a DIFFERENT group. Refuse deletion otherwise.
$targetGroupId = "/subscriptions/$subscription/resourceGroups/$labGroup"
if ($protectedOpenaiId.StartsWith($targetGroupId + '/', [StringComparison]::OrdinalIgnoreCase)) { throw 'Protected model is inside deletion scope' }
# After export, reviewed inventory, disabled access and explicit deletion approval:
az group delete --subscription $subscription --name $labGroup
az group exists --subscription $subscription --name $labGroup
```

The final existence result must be `false`. Do not treat a submitted deletion request as completion.
Record the platform-managed infrastructure group while ACA exists and verify its managed cleanup too;
do not manually remove shared/platform groups to clear an error. Resource-group deletion is irreversible
as a group operation; see [Microsoft's deletion guidance](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/delete-resource-group).

Review and remove **only exact lab-created IDs** from the ledger that live outside the deleted group:
the runtime OpenAI role assignment, orphaned OpenAI private endpoint connection, lab-only Entra consent/
assignments/credentials/registrations, peerings and DNS links on reused networks, lab-scoped budget or
action group, and any separately approved migration/connectivity resources. Retain reused registrations,
networks, certificates and preexisting grants. Never delete the shared OpenAI account/deployment, change
GitHub visibility or remove the owner's local credentials. Close lab sessions and revoke lab-only secrets.

Verify no remaining billable lab resources or registry images outside the deleted group. Check cost
analysis again after billing data catches up; deleted resources can still appear as historical charges.
Record actual cost and remaining shared-model cost separately. Finally run local live launch, approved
one-query verification, full replay/tests and stop; save those results as the post-cleanup portability gate.

For redeployment, start from the saved private commit and parameters, repeat identity/network/cost
preflight and obtain new provisioning approval. New group/identity IDs require new role assignments and
SQL client-ID SID mapping; do not reuse stale IDs or recreate expired credentials from evidence files.
