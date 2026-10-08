"""Trusted reporting contract. Model/database text cannot modify this module."""

VIEWS: dict[str, dict[str, str]] = {
    "vCustomers": {
        "CustomerId": "INT",
        "CustomerName": "VARCHAR",
        "Region": "VARCHAR",
        "Segment": "VARCHAR",
    },
    "vJobs": {
        "JobId": "INT",
        "CustomerId": "INT",
        "StartDate": "DATE",
        "Status": "VARCHAR",
        "ContractValue": "DECIMAL",
        "BudgetAmount": "DECIMAL",
    },
    "vInvoices": {
        "InvoiceId": "INT",
        "JobId": "INT",
        "InvoiceDate": "DATE",
        "Amount": "DECIMAL",
    },
    "vExpenses": {
        "ExpenseId": "INT",
        "JobId": "INT",
        "ExpenseDate": "DATE",
        "Category": "VARCHAR",
        "Amount": "DECIMAL",
    },
    "vTargets": {
        "TargetId": "INT",
        "PeriodStart": "DATE",
        "Region": "VARCHAR",
        "RevenueTarget": "DECIMAL",
        "MarginTargetPct": "DECIMAL",
    },
    "vJobFinancials": {
        "JobId": "INT",
        "CustomerId": "INT",
        "CustomerName": "VARCHAR",
        "Region": "VARCHAR",
        "Segment": "VARCHAR",
        "StartDate": "DATE",
        "Status": "VARCHAR",
        "ContractValue": "DECIMAL",
        "BudgetAmount": "DECIMAL",
        "TotalInvoiced": "DECIMAL",
        "TotalExpenses": "DECIMAL",
        "GrossMargin": "DECIMAL",
        "BudgetVariance": "DECIMAL",
    },
    "vMonthlyPerformance": {
        "PeriodStart": "DATE",
        "Region": "VARCHAR",
        "JobCount": "INT",
        "ContractValue": "DECIMAL",
        "TotalInvoiced": "DECIMAL",
        "TotalExpenses": "DECIMAL",
        "GrossMargin": "DECIMAL",
        "RevenueTarget": "DECIMAL",
    },
}

GRAINS = {
    "vCustomers": "one row per customer",
    "vJobs": "one row per job",
    "vInvoices": "one row per invoice (many invoices per job)",
    "vExpenses": "one row per expense (many expenses per job)",
    "vTargets": "one row per calendar month and region",
    "vJobFinancials": "one row per job; invoice and expense totals are pre-aggregated",
    "vMonthlyPerformance": "one row per job-start month and region; lifetime job amounts",
}

METRICS = {
    "Total Contract Value": "SUM(ContractValue) at job grain, CAD",
    "Total Invoiced": "SUM(TotalInvoiced) at job grain, CAD; not cash collected",
    "Total Expenses": "SUM(TotalExpenses) at job grain, CAD",
    "Gross Margin": "SUM(TotalInvoiced) - SUM(TotalExpenses), CAD",
    "Gross Margin Percentage": "100.0 * SUM(GrossMargin) / NULLIF(SUM(TotalInvoiced), 0)",
    "Job Count": "COUNT(*) at job grain",
    "Budget Variance": "SUM(BudgetAmount) - SUM(TotalExpenses); positive is favorable, CAD",
}


def schema_context() -> str:
    lines = ["Synthetic operations data; currency CAD; dates in 2025; no real customer data."]
    for name, columns in VIEWS.items():
        lines.append(f"reporting.{name} ({', '.join(columns)}): {GRAINS[name]}")
    lines.extend(f"{name}: {definition}" for name, definition in METRICS.items())
    lines.append(
        "Revenue is ambiguous: ask whether contract value or invoiced. "
        "MonthlyPerformance uses job-start cohorts, not invoice posting periods. "
        "Use vInvoices for invoice-date trends. Never join invoice and expense detail. "
        "Supported JOINs (one per SELECT, INNER or LEFT): vJobs/vJobFinancials to vCustomers on CustomerId; "
        "or vJobs/vJobFinancials to a ranked-invoice CTE on JobId AND its rank column = 1. "
        "A ranked-invoice CTE must select passthrough columns directly from vInvoices plus "
        "ROW_NUMBER() OVER (PARTITION BY JobId ORDER BY requested sort, InvoiceId) AS rn. "
        "Expose the unchanged JobId; no grouping, DISTINCT, TOP or joins inside that CTE. "
        "Include InvoiceId in the window order for deterministic ties. Use LEFT JOIN for every job, "
        "and put rn = 1 in ON to retain jobs without invoices (NULL InvoiceId and Amount). "
        "No cross joins, wildcard projections, arbitrary functions or recursive CTEs. "
        "Use @name parameters for user values; SELECT and nonrecursive CTEs only."
    )
    return "\n".join(lines)
