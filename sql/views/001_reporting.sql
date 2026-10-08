CREATE OR ALTER VIEW reporting.vCustomers AS
SELECT CustomerId, CustomerName, Region, Segment FROM ops.Customers;
GO
CREATE OR ALTER VIEW reporting.vJobs AS
SELECT JobId, CustomerId, StartDate, Status, ContractValue, BudgetAmount FROM ops.Jobs;
GO
CREATE OR ALTER VIEW reporting.vInvoices AS
SELECT InvoiceId, JobId, InvoiceDate, Amount FROM ops.Invoices;
GO
CREATE OR ALTER VIEW reporting.vExpenses AS
SELECT ExpenseId, JobId, ExpenseDate, Category, Amount FROM ops.Expenses;
GO
CREATE OR ALTER VIEW reporting.vTargets AS
SELECT TargetId, PeriodStart, Region, RevenueTarget, MarginTargetPct FROM ops.Targets;
GO
CREATE OR ALTER VIEW reporting.vJobFinancials AS
SELECT j.JobId, j.CustomerId, c.CustomerName, c.Region, c.Segment,
       j.StartDate, j.Status, j.ContractValue, j.BudgetAmount,
       COALESCE(i.TotalInvoiced, 0) AS TotalInvoiced,
       COALESCE(e.TotalExpenses, 0) AS TotalExpenses,
       COALESCE(i.TotalInvoiced, 0) - COALESCE(e.TotalExpenses, 0) AS GrossMargin,
       j.BudgetAmount - COALESCE(e.TotalExpenses, 0) AS BudgetVariance
FROM ops.Jobs AS j
JOIN ops.Customers AS c ON c.CustomerId = j.CustomerId
LEFT JOIN (SELECT JobId, SUM(Amount) AS TotalInvoiced FROM ops.Invoices GROUP BY JobId) AS i
  ON i.JobId = j.JobId
LEFT JOIN (SELECT JobId, SUM(Amount) AS TotalExpenses FROM ops.Expenses GROUP BY JobId) AS e
  ON e.JobId = j.JobId;
GO
CREATE OR ALTER VIEW reporting.vMonthlyPerformance AS
SELECT t.PeriodStart, t.Region, COALESCE(j.JobCount, 0) AS JobCount,
       COALESCE(j.ContractValue, 0) AS ContractValue,
       COALESCE(j.TotalInvoiced, 0) AS TotalInvoiced,
       COALESCE(j.TotalExpenses, 0) AS TotalExpenses,
       COALESCE(j.GrossMargin, 0) AS GrossMargin, t.RevenueTarget
FROM ops.Targets AS t
LEFT JOIN (
    SELECT DATEFROMPARTS(YEAR(StartDate), MONTH(StartDate), 1) AS PeriodStart,
           Region, COUNT(*) AS JobCount, SUM(ContractValue) AS ContractValue,
           SUM(TotalInvoiced) AS TotalInvoiced, SUM(TotalExpenses) AS TotalExpenses,
           SUM(GrossMargin) AS GrossMargin
    FROM reporting.vJobFinancials
    GROUP BY DATEFROMPARTS(YEAR(StartDate), MONTH(StartDate), 1), Region
) AS j ON j.PeriodStart = t.PeriodStart AND j.Region = t.Region;
