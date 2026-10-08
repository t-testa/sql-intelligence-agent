# Private Azure deployment preflight — October 8, 2026

**Status: preflight performed; billable provisioning awaits the cost/sequence exception below.**
No application resource group, VM, SQL database, container app or additional OpenAI account was created.
This is not an Azure acceptance report. The application remains runnable locally.

## Actual checks and changes

| Check | Actual result |
|---|---|
| Azure CLI | 2.89.1; subscription `Azure subscription 1` enabled; approved tenant and signed-in owner object ID match the privately recorded approval; account enabled |
| Deployment permissions | Existing subscription Owner assignment observed; no new subscription access granted |
| Existing resources | Reuse `sql-agent-openai-dev` in `rg-sql-agent-dev`, Canada East; no existing VNet, VPN, ACA environment or operator host to reuse |
| Existing model | `sql-agent-model`, GPT-4.1 mini `2025-04-14`, GlobalStandard; succeeded; 20 requests/minute and 20,000 tokens/minute |
| GitHub | `t-testa/sql-intelligence-agent` PRIVATE, Pages disabled; remote `main` and local starting commit both `7cce020b8658bfdfc8047954d4daf17a68ebc91a` |
| Entra registrations | Created `sql-intelligence-agent-lab-api` and `sql-intelligence-agent-lab-frontend`; both single tenant, separate IDs, assignment required, sole approved owner assigned |
| Delegated API permission | API v2 `access_as_user`; frontend requests only that delegated permission; consent is for the approved owner, not tenant-wide |
| Entra sign-in | Both enterprise applications deliberately **disabled**; no client secret or redirect URI created; real platform sign-in not executed |
| Provider readiness | Network, SQL, Compute and Insights registered; registration creates no billable workload |
| Bicep | All six templates compile with Bicep 0.47.16 |
| Initial foundation what-if | Succeeded: 28 creations, no modifications/deletions |
| Final foundation + operator what-if | Succeeded: **33 creations, no modifications/deletions, no diagnostics** |
| Windows regression | **467 passed, zero failures/errors**, including **220 security tests** and six direct SQL denials; no live model calls |
| Static checks | Ruff lint/format and strict mypy pass |
| Publication audit | Candidate files and Git history: zero Gitleaks findings; four configured credentials absent, including encoded forms; `.env`, ledger, raw evidence and temporary files ignored/untracked |
| Local portability | Existing SQL/API/UI healthy in Live mode; Live, Mock and Stop desktop shortcuts preserved; SQL volume and `.env` preserved |

Metadata was independently read back after Entra setup. The current CLI preflight intentionally remains
nonzero because the exact callback and enabled sign-in are not ready. Its GitHub CLI check also reports
unavailable (`gh` is not installed); a separate authenticated GitHub REST check and `git ls-remote`
established private visibility and the remote commit. This is recorded separately, not silently waived.

The first regression attempt found the local SQL container stopped and produced 310 passes/156 connection
errors. Starting the existing stack, preserving its volume, resolved that setup issue; the complete rerun
passed. No claim is made about why the container had previously stopped. The earlier 61/61 live-model
result remains historical local-SQL evidence; no new Azure-hosted live evaluation was run in this preflight.

## Exact proposed inventory

Region: Canada East. Dedicated application group: **`sqlintel-lab`**. The protected OpenAI account remains
in **`rg-sql-agent-dev`**. Real subscription/tenant/identity IDs, assignments and parameters remain in the
ignored `.local/azure-lab-ledger.json` and private parameter files.

| Resource | Name / quantity / configuration |
|---|---|
| ACA environment | `sqlintel-environment`; workload profiles v2, Consumption only, internal VIP, public networking disabled |
| Platform-managed infrastructure | Additional ACA-managed `ME_…` group, one Standard load balancer and one Standard outbound IPv4 charge; platform assigns final names |
| Applications | `sql-intelligence-api` and `sql-intelligence-web`; each 0.5 vCPU / 1 GiB, min 0, max 1 replica |
| Runtime identities | `sqlintel-runtime`, `sqlintel-frontend`; frontend has no SQL/OpenAI permission |
| VNet | `sqlintel-vnet`, `10.48.0.0/16`; ACA `/23`, endpoints `10.48.2.0/24`, maintenance `10.48.3.0/24`, browser `10.48.4.0/24` |
| Endpoint NSG | `sqlintel-endpoint-nsg`; app access; explicitly configured maintenance access; other inbound denied |
| Azure SQL | `sqlintel-izrxwizbxxpai`; Entra-only owner administration, TLS, public networking disabled, Proxy connection policy |
| Databases | `SQLIntelligence` and temporary `SQLIntelligenceValidation`; each Basic, 5 DTU, 2 GiB; deterministic synthetic fixtures |
| ACR | `sqlintelimagesizrxwi`, Basic, anonymous/admin access disabled; authenticated public registry endpoint, private images |
| Token storage | `sqlintelauthizrxwizb`, Standard LRS; private `auth-tokens` container, no shared key/public access |
| Private endpoints | `sqlintel-sql-pe`, `sqlintel-openai-pe`, `sqlintel-authstore-pe` |
| Private DNS | `privatelink.database.windows.net`, `privatelink.openai.azure.com`, `privatelink.blob.core.windows.net`, plus the generated ACA environment domain; VNet links and records |
| Logs / Insights | `sqlintel-logs`, `sqlintel-insights`; 30-day retention, workspace daily cap 1 GiB; no claim of automatic Python tracing |
| Private browser / maintenance host | `sqlintel-operator`, **Standard_D2as_v4**, Windows Server 2025 Desktop Experience, 2 vCPU / 8 GiB; pinned image `26100.33438.260905` |
| Operator disk / NIC / NSG | `sqlintel-operator-os`, 128 GiB E10 Standard SSD LRS; `sqlintel-operator-nic`; `sqlintel-operator-nsg` |
| Operator outbound IP | `sqlintel-operator-egress`, Standard static IPv4, explicit internet egress; all internet-initiated inbound traffic denied |
| Browser transport | `sqlintel-bastion`, **Developer** SKU only; no paid Bastion upgrade, VPN gateway, NAT gateway, Private DNS Resolver or Front Door |
| Cost monitoring | Owner-only budget notifications at 50/80/100%; include application group, ACA-managed group and reused OpenAI usage; review actual usage from lab start |

The final what-if covers the foundation and operator modules. App/auth resources, generated-domain DNS,
narrow RBAC assignments and budget settings are subsequent stages whose final parameters depend on
foundation outputs. Their live what-if/read-back remains required before applying those stages.
The platform-created load balancer/IP and VM OS disk are also billable even though their individual
creation is implicit. No endpoint is planned for the ACA environment itself.

The original B2s candidate was restricted for this subscription. B2s v2 was listed as available but its
family quota was zero; provider validation correctly rejected that proposal. D2as v4 has no listed
regional restriction, 10 family vCPUs available and 10 regional vCPUs available. The final what-if with
D2as v4 passed. This is not a guarantee of physical capacity at deployment time; do not silently choose
a larger or different-priced machine if allocation fails.

## Private browser, maintenance and callback sequence

The owner opens the Azure portal, connects through **Bastion Developer** to the Windows VM, then uses
Edge **inside that VM** to open the private Streamlit HTTPS address and sign in with the approved Entra
account. This is a practical browser route without buying a permanent VPN or DNS resolver. The local
Windows browser does not gain a direct network route to the application. Developer SKU has no native
client tunnel; do not promise a local-browser tunnel through it.

The VM's public IP is for explicit **outbound** access to Entra, updates and approved downloads.
The NIC NSG permits private RDP and denies every other inbound flow, including Internet RDP/HTTP/HTTPS.
The application, API, SQL and token store remain private. Test these denials from outside Azure.
The operator host has no managed identity or automatic SQL/model role.

Use the same VM in two sequential roles, never as an always-privileged browser host:

1. With application access and frontend ingress off, place its NIC in `operator-maintenance`.
   Only the approved owner signs in for SQL migration and independent references. The endpoint NSG
   permits 1433/443 from that reviewed subnet for SQL bootstrap and private Blob delegation/SAS issuance.
   Authentication is still required at every endpoint; this rule is not a database grant.
2. Bootstrap both synthetic databases, grant the runtime MI SELECT on approved views and DENY base
   access/writes/DDL, issue a short-lived user-delegation SAS and capture reference evidence.
3. Clear the operator's privileged CLI session; deallocate the VM; switch its NIC to `operator-browser`.
   Remove the maintenance rule by setting foundation `migrationSubnetPrefix=''`; review and apply
   that network update. Start the VM and verify SQL/blob connections fail from it before browser use.
   A future maintenance window reverses this deliberately with app access disabled.
4. VNet-linked private DNS resolves the four private zones from the VM and ACA. Keep the normal ACA
   hostname and platform TLS certificate; no custom domain/certificate purchase is needed.
5. The environment generates its domain only when created. Derive the exact frontend callback as
   `https://sql-intelligence-web.<environment-default-domain>/.auth/login/aad/callback`, then configure
   that **one** redirect URI, the short-lived OAuth secret and owner-only Easy Auth. No wildcard or
   temporary public callback is permitted.
6. Deploy frontend initially with `enablePrivateIngress=false` and API with access disabled. Read back
   the auth configuration, identities and private environment. Only then enable private frontend
   ingress and the two owner-assigned enterprise applications, perform real sign-in, and enable
   the owner's API acceptance window. A failed gate leaves access off.

This requires approval of a **staged callback gate**: registration metadata/offline authentication checks
are completed before provisioning; the generated callback and real login are completed after the
internal foundation exists and before application access. The callback cannot truthfully be marked
verified now. Private DNS, TLS, Bastion/RDP, token-store connectivity and actual sign-in are also not yet
executed tests. No other Entra user is created or invited for negative testing.

Remaining narrow grants, covered only as part of the private objective: runtime OpenAI User at the
existing account; AcrPull for the two app identities at this registry; the approved owner as SQL migration
administrator; owner-scoped Blob data/delegation permission for token-store issuance. Record exact new
assignment IDs and reuse existing assignments. Never grant another person access or widen subscription roles.

## Current resource-by-resource cost estimate

USD retail, Canada East/global meters read October 8, 2026; 730 hours/month, before tax/exchange rates.
These are estimates, not incurred charges. No reservations, paid networking add-ons or automatic SKU
upgrades are included. Selected raw meters are in [the pricing evidence](evidence/azure-preflight-prices-2026-10-08.json).

| Component | Rate / assumption | Estimated monthly USD |
|---|---|---:|
| Baseline SQL Basic | $0.1771/day | 5.39 |
| Temporary validation SQL Basic | Same | 5.39 |
| ACR Basic | $0.1666/day, images within included storage; local build | 5.07 |
| Three private endpoints | 3 × $0.01/hour | 21.90 |
| ACA-managed Standard load balancer | $0.025/hour, first five rules | 18.25 |
| ACA-managed outbound IPv4 | $0.005/hour | 3.65 |
| Four private DNS zones | $0.50/zone/month | 2.00 |
| Operator outbound IPv4 | $0.005/hour | 3.65 |
| Operator E10 OS disk | 128 GiB Standard SSD LRS | 10.56 |
| Operator Windows VM | $0.199/hour; 20–40 running hours, deallocated otherwise | 3.98–7.96 |
| Two ACA containers | 50–100 active hours each; unused subscription free grant | 0–7.56 |
| Existing GPT-4.1 mini | 1,000 questions, 2,500 input + 300 output tokens/question | 1.48 |
| Private Blob | 1 GiB and small token-store operation volume allowance | 0.25 |
| Log Analytics | 0–1 billable GiB beyond any applicable free allowance; $2.76/GiB | 0–2.76 |
| DNS queries, disk operations, LB/PE data | Light-use allowance; PE $0.01/GiB each direction, LB $0.005/GiB | 1.00 |
| VNet/subnets/NSGs/NIC/identities, Entra registrations, Bastion Developer, budget notifications | No separate base charge for this proposed configuration | 0 |
| **Light-use estimate** | Fixed portion about **$75.85**, before usage | **$82.56–96.86** |
| **Planning allowance** | Rounded contingency; not a service spending cap | **$85–100/month** |

The original US$20–40 estimate is insufficient for this topology. The managed load balancer and outbound
IP together add **$21.90/month**, even when app replicas scale to zero. The operator VM alone costs about
$145.27/month if left allocated continuously; deallocate it between sessions. Remove the second SQL
database only after preserving its acceptance evidence. Closing Streamlit tabs helps replicas scale down.

For a temporary **up-to-72-hour lab**, with at most 20 operator-VM hours, paced acceptance calls and prompt
cleanup, plan approximately **$12–18 total** and request a **US$20 before-tax allowance**. This is a planning
limit: Azure budgets alert rather than stop spending, metering may be delayed, and costs continue if
resources remain. Do not expand the window/SKU if the forecast exceeds that allowance. Private endpoint
partial hours round up; check actual invoices after teardown. Existing unrelated Azure usage is excluded.

No ACA environment private endpoint is selected; that feature would add the separate $0.12/hour
environment meter plus another endpoint. No VPN Gateway ($0.19/hour for VpnGw1) or Private DNS Resolver
($180/month per endpoint) is selected. ACR Premium is not needed for authenticated private images;
requiring its registry network endpoint to be private would be another budget/topology review.

Sources: [Azure retail API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices),
[ACA managed networking charges](https://learn.microsoft.com/en-us/azure/container-apps/custom-virtual-networks#managed-resources),
[ACA billing](https://learn.microsoft.com/en-us/azure/container-apps/billing),
[Private Link billing](https://azure.microsoft.com/en-us/pricing/details/private-link/),
[Bastion Developer availability and limits](https://learn.microsoft.com/en-us/azure/bastion/bastion-sku-comparison),
[Bastion portal access](https://learn.microsoft.com/en-us/azure/bastion/quickstart-host-portal),
[explicit outbound access](https://learn.microsoft.com/en-us/azure/virtual-network/ip-services/default-outbound-access).

## Approval boundary and remaining acceptance

The grouped exception request is for the named topology, its additional fixed charges/operator route,
the staged private callback, and a 72-hour/$20 lab window. Cleanup after evidence capture also needs
explicit authorization; preserve the existing OpenAI account, local files/volumes/shortcuts and private
GitHub repository. Do not treat this report, provider registration or a successful what-if as that approval.

After approval, follow [the runbook](AZURE_LAB_RUNBOOK.md), provision with access off, build and scan pinned
images, configure the narrow grants, seed SQL, then execute real private access/auth/MI/SQL tests, all
independent references and recorded replay, representative live queries and Learning Mode. Capture
sanitized screenshots/results. Real Entra login/MFA may require the owner to complete the sign-in screen.
No token or password should be pasted into chat or retained in screenshots. Do not claim Azure accuracy,
private connectivity or a validated release until these tests actually pass.

Raw evidence stays ignored: `artifacts/preflight-full-what-if.json`, `preflight-entra-metadata.json`,
`preflight-regression-ready.xml`, `preflight-retail-prices.json`, GitHub metadata and quota/SKU reports.
The ledger records created Entra objects and provider registrations. Deleting the lab group does not
delete Entra applications, consent or cross-group OpenAI assignments; remove only ledger-owned objects
after approval. Allow ACA to remove its managed infrastructure group; verify residual resources/billing.
Do not manually modify platform-managed load balancers. Preserve all redeployment inputs outside Azure.
