-- sql_runtime is created by the local bootstrap with a unique password.
-- Cloud: create a user for the managed identity and add it to the same role.
CREATE ROLE reporting_reader AUTHORIZATION dbo;
GRANT SELECT ON OBJECT::reporting.vCustomers TO reporting_reader;
GRANT SELECT ON OBJECT::reporting.vJobs TO reporting_reader;
GRANT SELECT ON OBJECT::reporting.vInvoices TO reporting_reader;
GRANT SELECT ON OBJECT::reporting.vExpenses TO reporting_reader;
GRANT SELECT ON OBJECT::reporting.vTargets TO reporting_reader;
GRANT SELECT ON OBJECT::reporting.vJobFinancials TO reporting_reader;
GRANT SELECT ON OBJECT::reporting.vMonthlyPerformance TO reporting_reader;
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::ops TO reporting_reader;
DENY INSERT, UPDATE, DELETE ON SCHEMA::reporting TO reporting_reader;
DENY EXECUTE TO reporting_reader;
DENY CREATE TABLE, CREATE VIEW, CREATE PROCEDURE, CREATE FUNCTION TO reporting_reader;
DENY ALTER ANY SCHEMA, ALTER ANY USER, ALTER ANY ROLE TO reporting_reader;
ALTER ROLE reporting_reader ADD MEMBER sql_runtime;
