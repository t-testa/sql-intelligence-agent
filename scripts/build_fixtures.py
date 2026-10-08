"""Independent Decimal oracle + separately authored reference SQL. No model or example imports.

Run deliberately when reviewing a dataset change; tests never regenerate committed fixtures.
"""

import json
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from scripts.seed_data import dataset

# Independent SQL reference contract, not imported from the proposal/mock implementation.
REFERENCES: dict[str, tuple[list[str], str]] = {
    "contract": (
        ["TotalContractValue"],
        "SELECT SUM(ContractValue) AS TotalContractValue FROM reporting.vJobs",
    ),
    "invoiced": (["TotalInvoiced"], "SELECT SUM(Amount) AS TotalInvoiced FROM reporting.vInvoices"),
    "expenses": (["TotalExpenses"], "SELECT SUM(Amount) AS TotalExpenses FROM reporting.vExpenses"),
    "margin": (
        ["GrossMargin"],
        "SELECT SUM(TotalInvoiced) - SUM(TotalExpenses) AS GrossMargin FROM reporting.vJobFinancials",
    ),
    "margin_pct": (
        ["GrossMarginPct"],
        "SELECT ROUND(100.0 * (SUM(TotalInvoiced) - SUM(TotalExpenses)) / "
        "NULLIF(SUM(TotalInvoiced),0), 2) AS GrossMarginPct "
        "FROM reporting.vJobFinancials",
    ),
    "jobs": (["JobCount"], "SELECT COUNT(JobId) AS JobCount FROM reporting.vJobs"),
    "budget": (
        ["BudgetVariance"],
        "SELECT SUM(BudgetAmount) - SUM(TotalExpenses) AS BudgetVariance FROM reporting.vJobFinancials",
    ),
    "customers": (
        ["CustomerCount"],
        "SELECT COUNT(CustomerId) AS CustomerCount FROM reporting.vCustomers",
    ),
    "contract_region": (
        ["Region", "TotalContractValue"],
        "SELECT Region, SUM(ContractValue) AS TotalContractValue "
        "FROM reporting.vJobFinancials GROUP BY Region ORDER BY Region",
    ),
    "invoiced_region": (
        ["Region", "TotalInvoiced"],
        "SELECT Region, SUM(TotalInvoiced) AS TotalInvoiced "
        "FROM reporting.vJobFinancials GROUP BY Region ORDER BY Region",
    ),
    "expenses_region": (
        ["Region", "TotalExpenses"],
        "SELECT Region, SUM(TotalExpenses) AS TotalExpenses "
        "FROM reporting.vJobFinancials GROUP BY Region ORDER BY Region",
    ),
    "margin_region": (
        ["Region", "GrossMargin"],
        "SELECT Region, SUM(TotalInvoiced) - SUM(TotalExpenses) AS GrossMargin "
        "FROM reporting.vJobFinancials GROUP BY Region ORDER BY Region",
    ),
    "jobs_region": (
        ["Region", "JobCount"],
        "SELECT Region, COUNT(JobId) AS JobCount FROM reporting.vJobFinancials "
        "GROUP BY Region ORDER BY Region",
    ),
    "contract_status": (
        ["Status", "TotalContractValue"],
        "SELECT Status, SUM(ContractValue) AS TotalContractValue "
        "FROM reporting.vJobs GROUP BY Status ORDER BY Status",
    ),
    "expense_category": (
        ["Category", "TotalExpenses"],
        "SELECT Category, SUM(Amount) AS TotalExpenses "
        "FROM reporting.vExpenses GROUP BY Category ORDER BY Category",
    ),
    "invoices_count": (
        ["InvoiceCount"],
        "SELECT COUNT(InvoiceId) AS InvoiceCount FROM reporting.vInvoices",
    ),
    "expenses_count": (
        ["ExpenseCount"],
        "SELECT COUNT(ExpenseId) AS ExpenseCount FROM reporting.vExpenses",
    ),
    "north_contract": (
        ["TotalContractValue"],
        "SELECT SUM(ContractValue) AS TotalContractValue "
        "FROM reporting.vJobFinancials WHERE Region = 'North'",
    ),
    "completed": (
        ["JobCount"],
        "SELECT COUNT(JobId) AS JobCount FROM reporting.vJobs WHERE Status = 'Completed'",
    ),
    "over_budget": (
        ["JobId", "BudgetVariance"],
        "SELECT JobId, BudgetAmount - TotalExpenses AS BudgetVariance "
        "FROM reporting.vJobFinancials WHERE TotalExpenses > BudgetAmount ORDER BY JobId",
    ),
    "top_customers": (
        ["CustomerName", "TotalInvoiced"],
        "SELECT TOP 5 CustomerName, SUM(TotalInvoiced) AS TotalInvoiced "
        "FROM reporting.vJobFinancials GROUP BY CustomerName "
        "ORDER BY TotalInvoiced DESC, CustomerName",
    ),
    "monthly_invoiced": (
        ["InvoiceMonth", "TotalInvoiced"],
        "SELECT MONTH(InvoiceDate) AS InvoiceMonth, SUM(Amount) AS TotalInvoiced "
        "FROM reporting.vInvoices GROUP BY MONTH(InvoiceDate) ORDER BY InvoiceMonth",
    ),
    "target_region": (
        ["Region", "RevenueTarget"],
        "SELECT Region, SUM(RevenueTarget) AS RevenueTarget FROM reporting.vTargets "
        "GROUP BY Region ORDER BY Region",
    ),
    "margin_pct_region": (
        ["Region", "GrossMarginPct"],
        "SELECT Region, ROUND(100.0 * (SUM(TotalInvoiced) - SUM(TotalExpenses)) "
        "/ NULLIF(SUM(TotalInvoiced),0), 2) AS GrossMarginPct "
        "FROM reporting.vJobFinancials GROUP BY Region ORDER BY Region",
    ),
    "above_average": (
        ["JobId", "ContractValue"],
        "SELECT JobId, ContractValue FROM reporting.vJobs WHERE ContractValue > "
        "(SELECT SUM(ContractValue) / COUNT(JobId) FROM reporting.vJobs) ORDER BY JobId",
    ),
    "rank_regions": (
        ["Region", "TotalContractValue", "RegionRank"],
        "SELECT Region, SUM(ContractValue) AS TotalContractValue, "
        "ROW_NUMBER() OVER (ORDER BY SUM(ContractValue) DESC, Region) AS RegionRank "
        "FROM reporting.vJobFinancials GROUP BY Region ORDER BY RegionRank",
    ),
    "having": (
        ["CustomerId", "JobCount"],
        "SELECT CustomerId, COUNT(JobId) AS JobCount FROM reporting.vJobs "
        "GROUP BY CustomerId HAVING COUNT(JobId) >= 4 ORDER BY CustomerId",
    ),
}

# Privileged test-only reference uses correlated subqueries, independent of the reporting
# view's aggregate-then-join implementation. Never exposed as an agent tool.
ORACLE_SOURCE = """WITH oracle AS (
SELECT j.JobId, j.CustomerId, c.CustomerName, c.Region, c.Segment,
       j.StartDate, j.Status, j.ContractValue, j.BudgetAmount,
       (SELECT SUM(i.Amount) FROM ops.Invoices i WHERE i.JobId=j.JobId) AS TotalInvoiced,
       (SELECT SUM(e.Amount) FROM ops.Expenses e WHERE e.JobId=j.JobId) AS TotalExpenses
FROM ops.Jobs j INNER JOIN ops.Customers c ON c.CustomerId=j.CustomerId
)
"""


def privileged_reference(sql: str) -> str:
    has_financials = "reporting.vJobFinancials" in sql
    sql = sql.replace("reporting.vJobFinancials", "oracle")
    for name in ("Customers", "Jobs", "Invoices", "Expenses", "Targets"):
        sql = sql.replace("reporting.v" + name, "ops." + name)
    return (ORACLE_SOURCE if has_financials else "") + sql


def fixtures() -> dict[str, Any]:
    data = dataset()
    customers = {row["CustomerId"]: row for row in data["Customers"]}
    invoice_totals: dict[int, Decimal] = defaultdict(Decimal)
    expense_totals: dict[int, Decimal] = defaultdict(Decimal)
    for row in data["Invoices"]:
        invoice_totals[row["JobId"]] += row["Amount"]
    for row in data["Expenses"]:
        expense_totals[row["JobId"]] += row["Amount"]
    jobs = []
    for source in data["Jobs"]:
        job = {**source, **customers[source["CustomerId"]]}
        job["TotalInvoiced"] = invoice_totals[job["JobId"]]
        job["TotalExpenses"] = expense_totals[job["JobId"]]
        job["GrossMargin"] = job["TotalInvoiced"] - job["TotalExpenses"]
        job["BudgetVariance"] = job["BudgetAmount"] - job["TotalExpenses"]
        jobs.append(job)

    def total(field: str, rows: list[dict[str, Any]] = jobs) -> Decimal:
        return sum((row[field] for row in rows), Decimal(0))

    def group(rows: list[dict[str, Any]], key: str, field: str | None) -> list[list[Any]]:
        groups: dict[Any, Decimal] = defaultdict(Decimal)
        for row in rows:
            groups[row[key]] += row[field] if field else Decimal(1)
        return [[key, value] for key, value in sorted(groups.items())]

    def percent(rows: list[dict[str, Any]]) -> Decimal:
        return (total("GrossMargin", rows) * 100 / total("TotalInvoiced", rows)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    results: dict[str, list[list[Any]]] = {
        "contract": [[total("ContractValue")]],
        "invoiced": [[total("TotalInvoiced")]],
        "expenses": [[total("TotalExpenses")]],
        "margin": [[total("GrossMargin")]],
        "margin_pct": [[percent(jobs)]],
        "jobs": [[len(jobs)]],
        "budget": [[total("BudgetVariance")]],
        "customers": [[len(customers)]],
        "invoices_count": [[len(data["Invoices"])]],
        "expenses_count": [[len(data["Expenses"])]],
        "north_contract": [[total("ContractValue", [j for j in jobs if j["Region"] == "North"])]],
        "completed": [[sum(j["Status"] == "Completed" for j in jobs)]],
        "over_budget": [[j["JobId"], j["BudgetVariance"]] for j in jobs if j["BudgetVariance"] < 0],
        "above_average": [
            [j["JobId"], j["ContractValue"]]
            for j in jobs
            if j["ContractValue"] > total("ContractValue") / len(jobs)
        ],
    }
    for prefix, field in [
        ("contract", "ContractValue"),
        ("invoiced", "TotalInvoiced"),
        ("expenses", "TotalExpenses"),
        ("margin", "GrossMargin"),
        ("jobs", None),
    ]:
        results[prefix + "_region"] = group(jobs, "Region", field)
    results["contract_status"] = group(jobs, "Status", "ContractValue")
    results["expense_category"] = group(data["Expenses"], "Category", "Amount")
    results["top_customers"] = sorted(
        group(jobs, "CustomerName", "TotalInvoiced"), key=lambda row: (-row[1], row[0])
    )[:5]
    monthly = [{**i, "Month": i["InvoiceDate"].month} for i in data["Invoices"]]
    results["monthly_invoiced"] = group(monthly, "Month", "Amount")
    results["target_region"] = group(data["Targets"], "Region", "RevenueTarget")
    results["margin_pct_region"] = [
        [r, percent([j for j in jobs if j["Region"] == r])] for r in sorted({j["Region"] for j in jobs})
    ]
    ranks = sorted(group(jobs, "Region", "ContractValue"), key=lambda row: (-row[1], row[0]))
    results["rank_regions"] = [[*row, index] for index, row in enumerate(ranks, 1)]
    results["having"] = [row for row in group(jobs, "CustomerId", None) if row[1] > 3]
    return {
        key: {
            "columns": cols,
            "rows": results[key],
            "reference_sql": sql,
            "privileged_sql": privileged_reference(sql),
        }
        for key, (cols, sql) in REFERENCES.items()
    }


def main() -> None:
    path = Path("sql/seeds/expected_results.json")
    path.write_text(json.dumps(fixtures(), indent=2, default=str) + "\n", encoding="utf-8")
    print(f"Wrote {len(REFERENCES)} independent expected-result fixtures to {path}")


if __name__ == "__main__":
    main()
