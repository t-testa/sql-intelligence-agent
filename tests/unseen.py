"""Held-out proposals for offline provider/SQL tests, deliberately absent from MockProvider."""

HIGHEST_QUESTION = (
    "For every job, show the invoice with the highest amount. Include JobID, InvoiceID, and Amount. "
    "Use ROW_NUMBER() to handle the ranking."
)

HIGHEST_SQL = """WITH RankedInvoices AS (
    SELECT JobId, InvoiceId, Amount,
           ROW_NUMBER() OVER (PARTITION BY JobId ORDER BY Amount DESC, InvoiceId ASC) AS rn
    FROM reporting.vInvoices
)
SELECT j.JobId AS JobID, r.InvoiceId AS InvoiceID, r.Amount
FROM reporting.vJobs AS j
LEFT JOIN RankedInvoices AS r ON j.JobId = r.JobId AND r.rn = 1
ORDER BY j.JobId"""

UNSEEN = [
    (HIGHEST_QUESTION, HIGHEST_SQL, []),
    (
        "For each job with invoices, show its latest invoice and invoice date.",
        """WITH latest AS (
        SELECT JobId, InvoiceId, InvoiceDate,
        ROW_NUMBER() OVER (PARTITION BY JobId ORDER BY InvoiceDate DESC, InvoiceId DESC) AS rn
        FROM reporting.vInvoices)
        SELECT JobId, InvoiceId, InvoiceDate FROM latest WHERE rn = 1 ORDER BY JobId""",
        [],
    ),
    (
        "Show customers with more than two completed jobs, including their total contract value.",
        """SELECT c.CustomerId, c.CustomerName, COUNT(*) AS CompletedJobs, SUM(j.ContractValue) AS Value
        FROM reporting.vJobs AS j JOIN reporting.vCustomers AS c ON j.CustomerId = c.CustomerId
        WHERE j.Status = @status GROUP BY c.CustomerId, c.CustomerName
        HAVING COUNT(*) > @minimum ORDER BY c.CustomerId""",
        [{"name": "status", "value": "Completed"}, {"name": "minimum", "value": 2}],
    ),
    (
        "Show January invoice totals per job and their previous invoice amount in InvoiceID order.",
        """SELECT JobId, InvoiceId, Amount, SUM(Amount) OVER (PARTITION BY JobId) AS JobTotal,
        LAG(Amount) OVER (PARTITION BY JobId ORDER BY InvoiceId) AS PreviousAmount
        FROM reporting.vInvoices WHERE InvoiceDate >= @start AND InvoiceDate < @end
        ORDER BY JobId, InvoiceId""",
        [{"name": "start", "value": "2025-01-01"}, {"name": "end", "value": "2025-02-01"}],
    ),
]
