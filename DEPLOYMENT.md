# Deployment and operations

For local SQL/UI with live Azure inference using an approved existing resource, follow
[LIVE_AZURE_OPENAI.md](LIVE_AZURE_OPENAI.md). It does not require the full M2 infrastructure deployment.

## Local M1

`docker compose --profile app up -d --build` starts an isolated SQL Server Developer database,
one-shot migration, FastAPI and Streamlit. Ports bind to 127.0.0.1 only: SQL 14339, API 8000, UI 8501.
The database volume belongs to the `sql-intelligence-agent` Compose project. Runtime containers use
a non-root user, read-only root filesystems and dropped Linux capabilities. Containers have bounded
SQL concurrency; use one API process for the configured three-query global limit.

Inspect only this project's services with `docker compose ps` and `docker compose logs --tail 50`.
`/health` is liveness; the SQL least-privilege check runs on API startup. A later SQL outage causes
queries to fail with a sanitized 503. Stop/restart with `docker compose stop` / `docker compose start`.
Bootstrap creates and seeds once; on restart it verifies source counts and refuses to overwrite
unexpected existing data. It is not yet a general schema migration/versioning system.

## M2 approval and sequence

No Azure deployment is authorized by the build request. Before provisioning, the owner must approve
subscription, dedicated resource group, region, identities, private access path and estimated costs.
Do not modify existing project resources. The supplied templates are preparation for that review.

1. Compile `infrastructure/main.bicep` and `application.bicep` locally. Compilation is not deployment.
2. Select a supported Azure OpenAI region/model/version and confirm quota. Create an Entra API app
   registration with delegated `access_as_user` scope, an explicit user allowlist, and an approved
   SQL administrator group. Registration and consent are tenant-admin activities outside this build.
3. Review a parameterized `az deployment group what-if` against a newly approved resource group.
   `main.bicep` defines an internal Container Apps environment, separate subnets, private SQL and
   OpenAI endpoints/DNS, managed identity, logs and Application Insights. SQL public networking and
   OpenAI local-key auth are disabled. A resource-scoped OpenAI User grant is the only runtime RBAC
   grant. Optional Key Vault is disabled by default and needs its own private endpoint if enabled.
4. Only after approval, deploy the foundation. Choose and deploy a Responses-compatible model
   explicitly; the template does not allocate a model or silently consume quota.
5. From an approved private-network migration host, use the privileged Entra identity to create the
   five tables, seed and views. Create the contained `sql_runtime` user bound to the runtime managed
   identity's object ID; review the supported Entra user-creation syntax for the target SQL service.
   Apply the reviewed `reporting_reader` grants/denials, then add that user to the role. Do not use
   the local SA bootstrap in Azure. The runtime must pass the same least-privilege tests.
6. Build, scan and push the image to an approved registry. Use an immutable digest. The sample
   application template expects an image that the environment can pull; private ACR requires a
   reviewed registry-identity configuration and resource-scoped AcrPull assignment, not a password.
7. Deploy `application.bicep` with the approved user IDs, API audience, model deployment and foundation
   outputs. It exposes only a private API. Entra tokens are verified by the API itself; it never trusts
   injected Easy Auth headers. Pin one replica until distributed query/request limits are implemented.
8. Implement and verify the cloud frontend's delegated login/token propagation before deploying it.
   The M1 frontend intentionally refuses cloud mode. Add the approved private user access path and
   internal DNS; neither public ingress nor blanket network bypass is part of this deployment.
9. Verify allowed and denied users, audience/tenant/scope failures, MI token renewal, private DNS,
   TLS verification, database DENY, deadlines, capacity, model refusals and answer accuracy. Re-run the
   reference corpus with live Azure proposals; report ambiguity and failures separately.
10. Wire Application Insights instrumentation/alerts and protected audit retention. The resource exists
    in the template, but application tracing and operational alert response remain M2 work.

## Cost estimation

Use the current Azure pricing calculator for the chosen region, currency and approved model. Record
the estimate date and assumptions; this repository does not claim a fixed monthly price.

| Component | Estimate inputs |
|---|---|
| Azure SQL | Basic database hours (about 730/month), storage, retention/backups |
| Container Apps | API/frontend vCPU and GiB seconds, requests, environment/network baseline charges |
| Azure OpenAI | Questions × average input/output tokens × selected model's current token prices |
| Private networking | Two private endpoints, processed data, DNS; optional access gateway/VPN |
| Monitoring | Ingested log GiB/day, retention, query/export costs and alerts |
| Registry | Chosen registry tier, storage, private endpoint and image transfer |
| Key Vault | Only if enabled: operations, storage and its private connectivity |

Use low/expected/high traffic scenarios and an explicit monthly budget alert. Check rate limits and
caps; a log daily quota is not a full Azure spending cap. Local SQL Server Developer is for development
and testing, not a production licensing choice.

## Cleanup

Local stop: `docker compose stop`. Remove containers while preserving data: `docker compose down`.
Delete only this project's disposable synthetic database when intended: `docker compose down -v`.

For an approved future Azure deployment, inspect the dedicated group's contents first:

```powershell
az resource list --resource-group <approved-dedicated-group> --output table
# Only after confirming that every listed resource belongs to this disposable deployment:
az group delete --name <approved-dedicated-group>
```

Retain needed evaluation/audit evidence before deletion. Remove project-specific Entra registrations,
consents and external registry images separately after review. Key Vault purge protection, if enabled,
means deletion is soft/recoverable for its retention period; do not assume immediate permanent removal.
