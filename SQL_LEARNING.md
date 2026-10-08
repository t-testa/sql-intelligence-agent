# SQL Learning Mode

SQL Learning Mode is a permanent application feature. Its sidebar toggle controls lesson visibility;
it does not remove the SQL display or change authorization. Live and mock modes both provide lessons.

Start the app and select **Show total invoiced by region**. Results, Generated SQL and Learn & practice
show the execution result, exact validated SQL/parameters and lessons tied to its AST.

## Learning progression

| Stage | Example | Focus |
|---|---|---|
| 1 | How many jobs are there? | SELECT, COUNT and job grain |
| 2 | What is contract value in the North region? | WHERE and parameterization |
| 3 | Show total invoiced by region. | GROUP BY and SUM |
| 4 | Which customers have more than three jobs? | WHERE versus HAVING |
| 5 | Show job count by region. | Many-to-one JOIN on CustomerId |
| 6 | Which jobs have above-average contract value? | Uncorrelated subquery |
| 7 | Rank regions by contract value using a CTE. | CTE and ROW_NUMBER |
| 8 | Show gross margin percentage by region. | Ratios of sums and NULLIF |

Logical processing: FROM/JOIN → WHERE → GROUP BY → HAVING → SELECT/window calculations → ORDER BY →
TOP. The optimizer may use a different physical plan; this lesson is not a retrieved execution plan.

Invoice and expense tables each contain multiple rows per job. Joining both details creates a product
of their row counts. Aggregating later does not repair it. Use `vJobFinancials`, whose aggregates are
computed independently first. `SUM(DISTINCT Amount)` is also incorrect when different legitimate
transactions share an amount. Compare margin as a ratio of sums, not an average of percentages.

## Practice

Write an alternative SQL query for a verified example and click **Validate & compare**. The same
gateway checks it before any execution. A separately authored reference query must match the committed
Decimal fixture, then candidate/reference rows are compared exactly. If the independent reference has
an outer ORDER BY, row order must match; otherwise comparison uses a multiset retaining duplicates.
Column positions matter; aliases may differ. Numeric values are compared without rounding away small
errors, and NULL remains distinct from zero. The interface shows
the independent reference SQL and result. A match proves only equivalence on this dataset.

With the pinned Streamlit version, a form submission may return to the Results tab. The completion
toast confirms evaluation; reopen Learn & practice for the saved comparison. Parameters remain the
values displayed with the original query. Unknown/new Azure questions have lessons but no practice
reference until a human authors and verifies one.

Try `COUNT(JobId)` in place of `COUNT(*)` for the job-count example: both return 240 because JobId is a
non-null primary key. Try adding `+ 1`: comparison should fail. Try a base table or DELETE: policy
rejects it. Ask “What is revenue?”: mock mode requests clarification rather than choosing a definition.

Performance lessons: filter dates with ranges where possible, select needed columns, avoid unnecessary
detail joins, and aggregate before display. TOP is explicit and does not substitute for a precise
business question. Result limits never modify the aggregate calculation.
