# Live Azure OpenAI runbook

## Inspection findings

The application already had an Azure Responses provider. It uses the standard OpenAI Python SDK,
the resource's `/openai/v1/responses` endpoint and one strict `propose_query` function. The model's
deployment name comes from configuration. The 27 predefined questions belong only to `MockProvider`;
new live questions do not need entries in that catalog.

Both providers pass through `AgentService → SQLGateway.validate → SQLServerBackend.execute`.
Every proposal, including a follow-up, receives the same AST, view, column, join and parameter checks.
The database principal independently denies base-table access and writes. Execution keeps the existing
10-second SQL timeout, 500-row/256-KiB result bounds and three-request concurrency limit by default.
Results are never silently truncated. SQL authorization does not establish business correctness.

Before this preparation, Docker forced mock mode and the UI's chat history was display-only. Those
gaps are fixed. The live adapter now accepts bounded conversation context; resource origins and full
v1 base URLs normalize correctly; provider errors give sanitized configuration guidance. Automatic
provider retries are disabled, and output defaults to 4,000 tokens. Failed questions are never silently
replaced with mock answers or automatically regenerated.

## Required resources and configuration

For **local app + local SQL + live Azure inference**, the only cloud prerequisite is an approved Azure
OpenAI resource with an existing text-model deployment supporting Responses and strict function
calling, accessible from this workstation/container. For example, Microsoft's Responses list includes
`gpt-4.1-mini` version `2025-04-14`; use an approved available deployment, and confirm regional model
availability and quota. The API's `model` field is your **deployment name**, which may differ from the
underlying model name. See Microsoft's [Azure Responses guide](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/responses).

You do not need Azure SQL, Container Apps, Fabric, an Azure AI agent service, or a new app registration
to test local inference with a resource key. Keep the existing local SQL connection and API token.
If there is no approved resource/deployment, stop and approve the subscription, resource group,
region, model, capacity and costs before creating them. This runbook does not provision anything.

| Variable | Required value / behavior |
|---|---|
| `AGENT_MODE` | `azure` for host Python; default `mock`. Docker live override sets this explicitly. |
| `AZURE_OPENAI_ENDPOINT` | Resource origin, e.g. `https://YOUR-RESOURCE.openai.azure.com`; a `/openai/v1/` base URL also works. No project URL, deployment path, query string or key in the URL. |
| `AZURE_OPENAI_DEPLOYMENT` | Exact existing deployment name from Azure, not a guessed model ID. |
| `AZURE_OPENAI_API_KEY` | Resource key for local key authentication; leave empty to use Azure identity on the host. The local Docker override requires a key. |
| `AZURE_OPENAI_TOKEN_SCOPE` | Default `https://ai.azure.com/.default`; used only with identity authentication. |
| `AZURE_OPENAI_TIMEOUT_SECONDS` | Default `30`, allowed 5–45. No automatic retries. |
| `AZURE_OPENAI_MAX_OUTPUT_TOKENS` | Default `4000`, allowed 1000–8000. An incomplete response fails closed. |
| `APP_ENV`, `AUTH_MODE` | Keep both `local` for this workflow. Live inference does not require `APP_ENV=cloud`. |
| `LOCAL_API_TOKEN`, `SQL_*` | Keep the existing generated local token and restricted SQL credentials. |

No dated `AZURE_OPENAI_API_VERSION` or public `OPENAI_API_KEY` is used by this adapter. Endpoint,
deployment and credential must belong to the same approved resource. The endpoint must be reachable:
an existing private endpoint requires its approved VPN/VNet route and private DNS.

The API-key path works only when local/key authentication is enabled on that resource. For host
identity authentication, leave `AZURE_OPENAI_API_KEY` empty, sign in to the intended tenant using
`az login --tenant YOUR-TENANT-ID`, and use an identity authorized for Azure OpenAI inference
(normally the resource-scoped **Cognitive Services OpenAI User** role). `DefaultAzureCredential`
can select configured environment credentials before Azure CLI; check the intended identity. The
host's Azure CLI login is not automatically available inside Docker.

Full cloud hosting is separate: `APP_ENV=cloud` requires Entra user authorization, SQL managed identity,
certificate verification and managed identity for OpenAI. It disallows API keys. `AZURE_CLIENT_ID`
selects a user-assigned managed identity when supplied in the process environment. See
[DEPLOYMENT.md](DEPLOYMENT.md) for tenant/audience/user allowlist and infrastructure requirements;
the current Streamlit frontend still deliberately refuses cloud hosting until delegated sign-in is built.

## Configure and start: Docker with a resource key

Run commands from:

```powershell
Set-Location 'C:\Users\Tony\Documents\ChatGPT\SQL Database Agent\sql-intelligence-agent'
```

1. Privately edit the existing ignored `.env`. Preserve its SQL passwords and local API token. Set
   `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT` and `AZURE_OPENAI_API_KEY`. Keep `AGENT_MODE=mock`
   in this file if you want ordinary Docker launches to remain regression/demo runs. Do not paste keys
   into chat, command history or source files. `.env.example` lists the optional bounds.
2. Validate the configuration without network calls:

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.verify_live --check-config --docker
   ```

   This checks configuration syntax and key presence, not credential validity, network access, quota
   or deployment compatibility. With the currently unconfigured Azure settings it intentionally fails.
3. After approving inference use, start the existing local application with the explicit override:

   ```powershell
   docker compose -f compose.yaml -f compose.azure.yaml --profile app up -d --build --wait backend frontend
   ```

   Starting the app and loading `/health` or `/catalog` do not invoke the model. Submitting a question
   does. The override passes only the necessary AI settings to the backend, never the frontend or SQL
   administrator password. Avoid sharing `docker compose config` output because it expands secrets.
4. Open [the app](http://127.0.0.1:8501/). The sidebar must say **Live Azure OpenAI** and show the exact
   deployment. Start **New conversation** after changing modes. A healthy status alone does not prove
   Azure connectivity; inference is first exercised by the next step.

## Alternative: host Python with Azure identity or a key

Use the existing `.venv` and installed ODBC Driver 18. For identity, authenticate as described above;
for a key, put the key in `.env`. Set `AGENT_MODE=azure` in `.env`. Stop only the Docker API/UI to free
their ports and keep the seeded database running:

```powershell
docker compose stop backend frontend
docker compose up -d --wait sqlserver
.\.venv\Scripts\python.exe -m scripts.verify_live --check-config
.\.venv\Scripts\uvicorn.exe backend.api.main:create_app --factory --host 127.0.0.1 --port 8000
```

In another terminal at the same repository root:

```powershell
.\.venv\Scripts\streamlit.exe run frontend/app.py --server.address 127.0.0.1
```

Use one API worker: conversation memory and concurrency limits are process-local. Restart after
editing `.env`. Environment variables override `.env`, so remove stale shell overrides if the displayed
mode or deployment differs from the file.

## Verify the first dynamically generated query

After you authorize a billable inference request, run:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_live --allow-cloud-call
```

The helper first checks that the running API reports `azure` and the configured deployment. It reads
jobs/invoices through the restricted SQL principal and builds an independent Python maximum/tie oracle.
It then submits **one** question through the authenticated `/questions` route, with no automatic
retries. It saves the returned SQL, parameters, result and request/conversation IDs to ignored
`artifacts/first-live-query.json`, and checks ROW_NUMBER, column order, one row per job, tie behavior,
amounts and ordering. It returns a nonzero exit code on clarification, rejection or incorrect results.
The helper is sized for the shipped synthetic dataset; larger datasets can hit existing result bounds.

The question is your requested highest-invoice question, with explicit NULL and tie handling:

> For every job, show the invoice with the highest amount. Include JobID, InvoiceID, and Amount.
> Use ROW_NUMBER() to handle the ranking. Include jobs with no invoices with NULL InvoiceID and Amount.
> Break equal amounts by the lowest InvoiceID. Order by JobID.

The shipped seed should produce **240 rows**. Job 12 has two zero-amount invoices, so InvoiceID **23**
wins the tie. The seed has invoices for every job; a separate SQL integration test filters out all
qualifying invoices and confirms LEFT JOIN still returns all 240 jobs with NULL invoice values.
Generated SQL may vary; a compatible shape is:

```sql
WITH RankedInvoices AS (
    SELECT JobId, InvoiceId, Amount,
           ROW_NUMBER() OVER (
               PARTITION BY JobId ORDER BY Amount DESC, InvoiceId ASC
           ) AS rn
    FROM reporting.vInvoices
)
SELECT j.JobId AS JobID, r.InvoiceId AS InvoiceID, r.Amount
FROM reporting.vJobs AS j
LEFT JOIN RankedInvoices AS r ON j.JobId = r.JobId AND r.rn = 1
ORDER BY j.JobId;
```

You can instead submit the original question in the UI and inspect **Generated SQL** and **Results**;
that is another billable request. The smoke helper's conversation is independent of the browser's.

## Supported questions and conversation behavior

New live questions can combine nonrecursive CTEs, supported aggregations/HAVING, uncorrelated subqueries,
parameterized filters and window functions such as ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD and windowed
SUM. Joins remain deliberate: a job/job-financial row to its customer on CustomerId, or to one ranked
invoice on JobId with `rn = 1` in ON. The ranked relation must expose unchanged JobId, use ROW_NUMBER
partitioned only by JobId and include InvoiceId in its ordering. Arbitrary detail joins, invoice/expense
fanout, recursive CTEs, external sources, wildcard projections and unreviewed functions remain blocked.
The model receives these restrictions and can ask clarifications. Not every valid T-SQL query is supported.

`/questions` accepts an optional server-issued `conversation_id` and returns it on every successful
answer or clarification. Subsequent requests must echo it. The UI does this automatically. Context
contains questions and accepted proposal JSON (clarifications or validated SQL/parameters), never
database result cells. “Only East” or an answer to “contract value or invoiced?” can therefore retain
the previous question. References to individual result rows require explicit IDs.

Sessions belong to the authenticated subject and are serialized per conversation. Memory supports
128 sessions, up to 12 accepted turns and a 32,000-character history threshold (a final bounded turn
can cross the threshold). It expires after 30 minutes idle or API restart. Full/expired sessions return
409 with an instruction to start a new conversation; context is never silently trimmed. **New
conversation** clears the old server session and UI history. This is bounded local memory, not durable
multi-replica storage. In local mode all calls use the workstation operator identity. Mock mode remains
the same fixed catalog; it does not gain natural-language follow-up reasoning.

## Failures and return to mock mode

The app reports sanitized guidance for Azure 401 (credential), 403 (role/network), 404 (endpoint or
deployment), 429 (quota/rate), timeout and malformed/incomplete tool output. These appear as API 502
with the Azure failure described in `detail`. SQL policy failures are 422; they never bypass validation.
A model may still generate unsupported or semantically wrong SQL. Inspect the first result before
relying on further answers. Increasing tokens does not fix a wrong endpoint or unsupported model.

For Docker, omit the override to return to mock mode:

```powershell
docker compose --profile app up -d --wait backend frontend
```

For host Python, set `AGENT_MODE=mock` and restart the API. The Docker test profile explicitly forces
mock mode and clears Azure provider credentials, even if `.env` contains live configuration.
Run the existing regression suite with:

```powershell
$env:RUN_SQL_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest -q
docker compose --profile test run --build --rm tests
```

No Azure resource was created and no live inference was invoked while preparing this change. Offline
SDK transport tests and real SQL Server execution tests establish the application path; they do not
measure an Azure model's ability to generate correct SQL. First live verification awaits your configured
resource, credentials and explicit decision to run a billable request.
