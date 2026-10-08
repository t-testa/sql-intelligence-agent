"""Deterministic mock proposals. These contain no expected answers."""

from dataclasses import dataclass

from backend.contracts import Parameter


@dataclass(frozen=True)
class Example:
    id: str
    question: str
    sql: str
    parameters: tuple[tuple[str, str], ...] = ()

    def bindings(self) -> list[Parameter]:
        return [Parameter(name=name, value=value) for name, value in self.parameters]


EXAMPLES = [
    Example(
        "contract",
        "What is total contract value?",
        "SELECT SUM(ContractValue) AS TotalContractValue FROM reporting.vJobFinancials",
    ),
    Example(
        "invoiced",
        "What is total invoiced?",
        "SELECT SUM(TotalInvoiced) AS TotalInvoiced FROM reporting.vJobFinancials",
    ),
    Example(
        "expenses",
        "What are total expenses?",
        "SELECT SUM(TotalExpenses) AS TotalExpenses FROM reporting.vJobFinancials",
    ),
    Example(
        "margin",
        "What is gross margin?",
        "SELECT SUM(GrossMargin) AS GrossMargin FROM reporting.vJobFinancials",
    ),
    Example(
        "margin_pct",
        "What is gross margin percentage?",
        "SELECT ROUND(100.0 * SUM(GrossMargin) / NULLIF(SUM(TotalInvoiced), 0), 2) "
        "AS GrossMarginPct FROM reporting.vJobFinancials",
    ),
    Example("jobs", "How many jobs are there?", "SELECT COUNT(*) AS JobCount FROM reporting.vJobs"),
    Example(
        "budget",
        "What is budget variance?",
        "SELECT SUM(BudgetVariance) AS BudgetVariance FROM reporting.vJobFinancials",
    ),
    Example(
        "customers",
        "How many customers are there?",
        "SELECT COUNT(*) AS CustomerCount FROM reporting.vCustomers",
    ),
    Example(
        "contract_region",
        "Show contract value by region.",
        "SELECT Region, SUM(ContractValue) AS TotalContractValue "
        "FROM reporting.vJobFinancials GROUP BY Region ORDER BY Region",
    ),
    Example(
        "invoiced_region",
        "Show total invoiced by region.",
        "SELECT Region, SUM(TotalInvoiced) AS TotalInvoiced "
        "FROM reporting.vJobFinancials GROUP BY Region ORDER BY Region",
    ),
    Example(
        "expenses_region",
        "Show expenses by region.",
        "SELECT Region, SUM(TotalExpenses) AS TotalExpenses "
        "FROM reporting.vJobFinancials GROUP BY Region ORDER BY Region",
    ),
    Example(
        "margin_region",
        "Show gross margin by region.",
        "SELECT Region, SUM(GrossMargin) AS GrossMargin "
        "FROM reporting.vJobFinancials GROUP BY Region ORDER BY Region",
    ),
    Example(
        "jobs_region",
        "Show job count by region.",
        "SELECT c.Region, COUNT(*) AS JobCount FROM reporting.vJobs AS j "
        "JOIN reporting.vCustomers AS c ON j.CustomerId = c.CustomerId "
        "GROUP BY c.Region ORDER BY c.Region",
    ),
    Example(
        "contract_status",
        "Show contract value by job status.",
        "SELECT Status, SUM(ContractValue) AS TotalContractValue "
        "FROM reporting.vJobs GROUP BY Status ORDER BY Status",
    ),
    Example(
        "expense_category",
        "Show expenses by category.",
        "SELECT Category, SUM(Amount) AS TotalExpenses "
        "FROM reporting.vExpenses GROUP BY Category ORDER BY Category",
    ),
    Example(
        "invoices_count",
        "How many invoices are there?",
        "SELECT COUNT(*) AS InvoiceCount FROM reporting.vInvoices",
    ),
    Example(
        "expenses_count",
        "How many expense records are there?",
        "SELECT COUNT(*) AS ExpenseCount FROM reporting.vExpenses",
    ),
    Example(
        "north_contract",
        "What is contract value in the North region?",
        "SELECT SUM(ContractValue) AS TotalContractValue "
        "FROM reporting.vJobFinancials WHERE Region = @region",
        (("region", "North"),),
    ),
    Example(
        "completed",
        "How many jobs are completed?",
        "SELECT COUNT(*) AS JobCount FROM reporting.vJobs WHERE Status = @status",
        (("status", "Completed"),),
    ),
    Example(
        "over_budget",
        "Which jobs are over budget?",
        "SELECT JobId, BudgetVariance FROM reporting.vJobFinancials WHERE BudgetVariance < 0 ORDER BY JobId",
    ),
    Example(
        "top_customers",
        "Who are the top five customers by invoiced amount?",
        "SELECT TOP 5 CustomerName, SUM(TotalInvoiced) AS TotalInvoiced "
        "FROM reporting.vJobFinancials GROUP BY CustomerName "
        "ORDER BY TotalInvoiced DESC, CustomerName",
    ),
    Example(
        "monthly_invoiced",
        "Show invoiced amount by invoice month.",
        "SELECT MONTH(InvoiceDate) AS InvoiceMonth, SUM(Amount) AS TotalInvoiced "
        "FROM reporting.vInvoices GROUP BY MONTH(InvoiceDate) ORDER BY InvoiceMonth",
    ),
    Example(
        "target_region",
        "Show revenue targets by region.",
        "SELECT Region, SUM(RevenueTarget) AS RevenueTarget "
        "FROM reporting.vTargets GROUP BY Region ORDER BY Region",
    ),
    Example(
        "margin_pct_region",
        "Show gross margin percentage by region.",
        "SELECT Region, ROUND(100.0 * SUM(GrossMargin) / NULLIF(SUM(TotalInvoiced), 0), 2) "
        "AS GrossMarginPct FROM reporting.vJobFinancials GROUP BY Region ORDER BY Region",
    ),
    Example(
        "above_average",
        "Which jobs have above-average contract value?",
        "SELECT JobId, ContractValue FROM reporting.vJobs WHERE ContractValue > "
        "(SELECT AVG(ContractValue) FROM reporting.vJobs) ORDER BY JobId",
    ),
    Example(
        "rank_regions",
        "Rank regions by contract value using a CTE.",
        "WITH totals AS (SELECT Region, SUM(ContractValue) AS TotalContractValue "
        "FROM reporting.vJobFinancials GROUP BY Region) "
        "SELECT Region, TotalContractValue, ROW_NUMBER() OVER "
        "(ORDER BY TotalContractValue DESC, Region) AS RegionRank "
        "FROM totals ORDER BY RegionRank",
    ),
    Example(
        "having",
        "Which customers have more than three jobs?",
        "SELECT CustomerId, COUNT(*) AS JobCount FROM reporting.vJobs "
        "GROUP BY CustomerId HAVING COUNT(*) > 3 ORDER BY CustomerId",
    ),
]

BY_ID = {example.id: example for example in EXAMPLES}
