-- Privileged migration identity only. Run once in an empty SQLIntelligence database.
CREATE SCHEMA ops AUTHORIZATION dbo;
GO
CREATE SCHEMA reporting AUTHORIZATION dbo;
GO
CREATE TABLE ops.Customers (
    CustomerId int NOT NULL CONSTRAINT PK_Customers PRIMARY KEY,
    CustomerName nvarchar(100) NOT NULL,
    Region nvarchar(20) NOT NULL,
    Segment nvarchar(20) NOT NULL,
    InternalNote nvarchar(200) NOT NULL
);
CREATE TABLE ops.Jobs (
    JobId int NOT NULL CONSTRAINT PK_Jobs PRIMARY KEY,
    CustomerId int NOT NULL CONSTRAINT FK_Jobs_Customers REFERENCES ops.Customers(CustomerId),
    StartDate date NOT NULL,
    Status nvarchar(20) NOT NULL CHECK (Status IN ('Completed','Active','Planned')),
    ContractValue decimal(18,2) NOT NULL CHECK (ContractValue >= 0),
    BudgetAmount decimal(18,2) NOT NULL CHECK (BudgetAmount >= 0)
);
CREATE TABLE ops.Invoices (
    InvoiceId int NOT NULL CONSTRAINT PK_Invoices PRIMARY KEY,
    JobId int NOT NULL CONSTRAINT FK_Invoices_Jobs REFERENCES ops.Jobs(JobId),
    InvoiceDate date NOT NULL,
    Amount decimal(18,2) NOT NULL CHECK (Amount >= 0)
);
CREATE TABLE ops.Expenses (
    ExpenseId int NOT NULL CONSTRAINT PK_Expenses PRIMARY KEY,
    JobId int NOT NULL CONSTRAINT FK_Expenses_Jobs REFERENCES ops.Jobs(JobId),
    ExpenseDate date NOT NULL,
    Category nvarchar(30) NOT NULL,
    Amount decimal(18,2) NOT NULL CHECK (Amount >= 0)
);
CREATE TABLE ops.Targets (
    TargetId int NOT NULL CONSTRAINT PK_Targets PRIMARY KEY,
    PeriodStart date NOT NULL,
    Region nvarchar(20) NOT NULL,
    RevenueTarget decimal(18,2) NOT NULL CHECK (RevenueTarget >= 0),
    MarginTargetPct decimal(5,2) NOT NULL CHECK (MarginTargetPct BETWEEN 0 AND 100),
    CONSTRAINT UQ_Targets_PeriodRegion UNIQUE (PeriodStart, Region)
);
CREATE INDEX IX_Jobs_CustomerDate ON ops.Jobs(CustomerId, StartDate);
CREATE INDEX IX_Invoices_Job ON ops.Invoices(JobId) INCLUDE (Amount, InvoiceDate);
CREATE INDEX IX_Expenses_Job ON ops.Expenses(JobId) INCLUDE (Amount, ExpenseDate);
