# Fabric and Power BI — M3 design

Status: no Fabric workspace, Lakehouse, pipeline, SQL endpoint, semantic model or report has been
created or modified. `QueryBackend` is the integration seam; `FabricSQLBackend` fails closed until
curated objects, permissions and endpoint capabilities have been verified. SQL Server success is not
evidence that every query will work on a Fabric SQL analytics endpoint.

## Explicitly approved ingestion workflow

1. Obtain the owner's approval for a **new, separate** Fabric workspace/Lakehouse and its capacity
   cost. Record workspace/Lakehouse IDs and the exact tables in a reviewed deployment manifest.
2. Use a separate ingestion identity and a Fabric pipeline/notebook to extract synthetic source
   tables from the approved Azure SQL source. The query-agent identity gets no ingestion permissions.
3. Land versioned staging data keyed by source seed version and load timestamp. Validate counts
   (60/240/480/720/48), primary/foreign keys, cents precision and the 27 committed result fixtures.
4. Publish curated `FactJobFinancials` only after independently grouping invoices and expenses by
   JobId. Publish `Targets`, `DimCustomer`, `DimRegion` and `DimMonth`. Materialize `JobStartMonth` as
   the first day of the job's start month. Use explicit column lists; exclude InternalNote.
5. Make refresh idempotent using a reviewed snapshot replacement/merge strategy. Keep the last valid
   snapshot and failed-load diagnostics. Scheduled writes require separate approval.
6. Wait for SQL analytics endpoint synchronization. Verify row counts, types, nulls and all reference
   totals through the endpoint. Grant its query identity only approved curated read access.

This is a pipeline specification, not an executable write tool. Implement and approve the ingestion
artifact in M3 before running it. The existing Customer Intelligence Agent and Fabric Operations
Intelligence projects are outside this repository's scope.

## Dialect and SQL editor workflow

Inventory actual endpoint support for casts, DATEPART, TOP, CTEs, window functions, parameter binding,
statement cancellation and identity authentication. Test each supported construct against a dedicated
synthetic endpoint. Add a backend-specific catalog and capability policy rather than loosening Azure
SQL's policy globally. Views, table permissions and database APIs differ by endpoint.

Copy validated SQL from **Generated SQL** into Fabric's SQL editor for human review. Map reporting view
names to approved curated table names explicitly. The editor does not receive this application's
bound parameters: declare typed local values in the editor or use an approved parameter workflow.
Do not insert user values using string interpolation. Editor-only DECLARE batches remain prohibited
in the agent. Independently verify the result before enabling the Fabric adapter.

## Semantic model

Create one-to-many, single-direction relationships:

| Dimension | Fact column | Target column |
|---|---|---|
| DimRegion[Region] | FactJobFinancials[Region] | Targets[Region] |
| DimMonth[MonthStart] | FactJobFinancials[JobStartMonth] | Targets[PeriodStart] |
| DimCustomer[CustomerId] | FactJobFinancials[CustomerId] | None |

Do not relate the two facts directly. Disable automatic date tables when using the explicit calendar.
Use fixed decimal data types for financial columns. Customer filters do not allocate regional targets;
label target visuals accordingly or hide them when slicing to an unsupported grain.

The supplied [DAX measures](docs/powerbi_measures.dax) mirror the SQL definitions. Validate them against
the committed fixtures at all-data, region, status and month levels. DAX definitions are provided but
have not been executed in a Power BI semantic model during M1.

## Example report design

**Operations overview**, 16:9 canvas:

| Area | Visual | Definition |
|---|---|---|
| Header | Title, refresh stamp, region and job-start month slicers | Show synthetic-data label |
| KPI row | Contract Value, Invoiced, Expenses, Margin, Margin %, Job Count | Use verified measures |
| Middle left | Monthly invoiced vs target, clustered columns/line | Explicitly label job-start cohort |
| Middle right | Gross Margin by Region, horizontal bars | Shared region filter |
| Lower left | Budget Variance by Job, diverging bars | Positive = favorable |
| Lower right | Customer/job matrix | Contract, invoiced, expense, margin and variance |

Use CAD units, two decimals where useful, a neutral background and distinct favorable/unfavorable
colors with text labels. Add a **Metric definitions** tooltip page. Add an **SQL reconciliation** page
with validation date, seed version and reference totals. A separate invoice-posting-month page needs
an invoice-date fact/calendar relationship and must not be labeled as the cohort target comparison.
