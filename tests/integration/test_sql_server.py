from decimal import Decimal

import pyodbc
import pytest

from backend.agent.examples import EXAMPLES
from backend.agent.provider import MockProvider
from backend.agent.service import AgentService, canonical_rows
from backend.config import Settings
from backend.contracts import ResultTable
from backend.database.connection import make_engine
from backend.database.executor import (
    BusyError,
    QueryTimeoutError,
    ResultLimitError,
    SQLServerBackend,
    scalar,
)
from backend.security.gateway import SQLGateway
from scripts.bootstrap_db import admin_connection

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.id)
def test_privileged_base_table_oracle(example, sql_backend, expected):
    fixture = expected[example.id]
    conn = admin_connection("SQLIntelligence")
    try:
        cursor = conn.execute(fixture["privileged_sql"])
        rows = [[scalar(v) for v in row] for row in cursor.fetchall()]
    finally:
        conn.close()
    actual = ResultTable(columns=fixture["columns"], rows=rows, row_count=len(rows), elapsed_ms=0)
    golden = ResultTable(
        columns=fixture["columns"],
        rows=fixture["rows"],
        row_count=len(fixture["rows"]),
        elapsed_ms=0,
    )
    assert canonical_rows(actual) == canonical_rows(golden)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM ops.Jobs",
        "SELECT InternalNote FROM ops.Customers",
        "UPDATE ops.Jobs SET ContractValue=ContractValue WHERE JobId=-1",
        "DELETE FROM ops.Expenses WHERE ExpenseId=-1",
        "CREATE TABLE reporting.unauthorized (x int)",
        "UPDATE reporting.vJobs SET ContractValue=ContractValue WHERE JobId=-1",
    ],
)
def test_database_itself_denies_unauthorized_actions(sql_backend, sql):
    conn = sql_backend.engine.raw_connection()
    try:
        with pytest.raises(pyodbc.Error):
            conn.cursor().execute(sql)
    finally:
        conn.rollback()
        conn.close()


def test_join_fanout_reference_demonstrates_inflation(sql_backend):
    conn = admin_connection("SQLIntelligence")
    try:
        bad = conn.execute(
            "SELECT SUM(i.Amount), SUM(e.Amount) FROM ops.Invoices i JOIN ops.Expenses e ON i.JobId=e.JobId"
        ).fetchone()
        invoices = conn.execute("SELECT SUM(Amount) FROM ops.Invoices").fetchval()
        expenses = conn.execute("SELECT SUM(Amount) FROM ops.Expenses").fetchval()
        good = conn.execute(
            "SELECT SUM(TotalInvoiced), SUM(TotalExpenses) FROM reporting.vJobFinancials"
        ).fetchone()
    finally:
        conn.close()
    assert bad[0] == 3 * invoices
    assert bad[1] == 2 * expenses
    assert tuple(good) == (invoices, expenses)


def test_margin_ratio_is_not_average_of_percentages(sql_backend):
    query = SQLGateway().validate(
        "SELECT AVG(100.0 * GrossMargin / NULLIF(TotalInvoiced,0)) AS Wrong, "
        "100.0 * SUM(GrossMargin) / NULLIF(SUM(TotalInvoiced),0) AS Correct "
        "FROM reporting.vJobFinancials"
    )
    row = sql_backend.execute(query).rows[0]
    assert abs(Decimal(str(row[0])) - Decimal(str(row[1]))) > Decimal("0.01")


def test_row_limit_rejects_instead_of_silent_truncation(sql_backend):
    with pytest.raises(ResultLimitError):
        sql_backend.execute(SQLGateway().validate("SELECT ExpenseId FROM reporting.vExpenses"))
    # Reusing the connection after cancellation must still work.
    assert sql_backend.execute(
        SQLGateway().validate("SELECT COUNT(*) AS Total FROM reporting.vExpenses")
    ).rows == [[720]]


def test_payload_limit(sql_backend):
    settings = Settings(max_result_bytes=1024)
    db = SQLServerBackend(make_engine(settings), settings)
    try:
        with pytest.raises(ResultLimitError):
            db.execute(SQLGateway().validate("SELECT CustomerName FROM reporting.vCustomers"))
    finally:
        db.engine.dispose()


def test_concurrency_limit(sql_backend):
    for _ in range(sql_backend.settings.max_concurrent_queries):
        sql_backend._slots.acquire()
    try:
        with pytest.raises(BusyError):
            sql_backend.execute(SQLGateway().validate("SELECT JobId FROM reporting.vJobs"))
    finally:
        for _ in range(sql_backend.settings.max_concurrent_queries):
            sql_backend._slots.release()


def test_database_lock_and_driver_deadline(sql_backend):
    settings = Settings(query_timeout_seconds=1)
    db = SQLServerBackend(make_engine(settings), settings)
    locker = admin_connection("SQLIntelligence")
    locker.autocommit = False
    try:
        locker.execute("UPDATE ops.Jobs WITH (TABLOCKX) SET ContractValue=ContractValue+1 WHERE JobId=1")
        with pytest.raises(QueryTimeoutError):
            db.execute(SQLGateway().validate("SELECT SUM(ContractValue) AS Total FROM reporting.vJobs"))
    finally:
        locker.rollback()
        locker.close()
        db.engine.dispose()


def test_learning_compares_independent_reference(sql_backend):
    service = AgentService(MockProvider(), sql_backend)
    assert service.practice("jobs", "SELECT COUNT(JobId) AS N FROM reporting.vJobs", [])["matches"]
    assert not service.practice("jobs", "SELECT COUNT(JobId)+1 AS N FROM reporting.vJobs", [])["matches"]


def test_parameter_injection_stays_data(sql_backend):
    from backend.contracts import Parameter

    query = SQLGateway().validate(
        "SELECT COUNT(*) AS N FROM reporting.vJobFinancials WHERE Region=@region",
        [Parameter(name="region", value="North'; DELETE FROM ops.Jobs; --")],
    )
    assert sql_backend.execute(query).rows == [[0]]
