import json
import sys
import threading
import time
from contextlib import suppress
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol

import pyodbc
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from backend.config import Settings
from backend.contracts import ResultTable, Scalar
from backend.security.gateway import ValidatedQuery


class ExecutionError(RuntimeError):
    pass


class ResultLimitError(ExecutionError):
    pass


class QueryTimeoutError(ExecutionError):
    pass


class BusyError(ExecutionError):
    pass


class QueryBackend(Protocol):
    name: str

    def execute(self, query: ValidatedQuery) -> ResultTable: ...


def scalar(value: Any) -> Scalar:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Decimal):
        return str(value)  # Preserve exact financial precision in the API.
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise ExecutionError("Database returned an unsupported value type")


class SQLServerBackend:
    name = "azure-sql"

    def __init__(self, engine: Engine, settings: Settings) -> None:
        self.engine = engine
        self.settings = settings
        self._slots = threading.BoundedSemaphore(settings.max_concurrent_queries)

    def verify_identity(self) -> None:
        with self.engine.connect() as conn:
            row = conn.exec_driver_sql(
                "SELECT USER_NAME(), IS_ROLEMEMBER('db_owner'), "
                "COALESCE(IS_SRVROLEMEMBER('sysadmin'),0), "
                "HAS_PERMS_BY_NAME('ops.Jobs','OBJECT','SELECT'), "
                "HAS_PERMS_BY_NAME('ops.Jobs','OBJECT','UPDATE'), "
                "HAS_PERMS_BY_NAME('reporting.vJobFinancials','OBJECT','SELECT')"
            ).one()
        if row[0] != self.settings.sql_expected_principal or tuple(row[1:]) != (0, 0, 0, 0, 1):
            raise ExecutionError("Runtime database principal failed the least-privilege startup check")

    def execute(self, query: ValidatedQuery) -> ResultTable:
        if not isinstance(query, ValidatedQuery):
            raise TypeError("Only gateway-validated queries may be executed")
        if not self._slots.acquire(blocking=False):
            raise BusyError("Query capacity is busy; retry shortly")
        started = time.monotonic()
        connection = None
        cursor = None
        try:
            connection = self.engine.raw_connection()
            cursor = connection.cursor()
            # Engine/driver cancellation timeout plus server-side lock wait limit.
            cursor.execute(f"SET LOCK_TIMEOUT {self.settings.query_timeout_seconds * 1000}")
            cursor.execute(query.bound_sql, query.values)
            columns = [str(column[0]) for column in cursor.description]
            if len(set(name.lower() for name in columns)) != len(columns):
                raise ExecutionError("Result column names must be unique")
            rows: list[list[Scalar]] = []
            size = len(json.dumps(columns).encode("utf-8")) + 256
            while True:
                if time.monotonic() - started > self.settings.query_timeout_seconds:
                    cursor.cancel()
                    raise QueryTimeoutError("Query exceeded the total result-reading deadline")
                row = cursor.fetchone()
                if row is None:
                    break
                if len(rows) >= self.settings.max_result_rows:
                    cursor.cancel()
                    raise ResultLimitError("Result exceeds row limit; aggregate or narrow the query")
                values = [scalar(value) for value in row]
                size += len(json.dumps(values, ensure_ascii=False, allow_nan=False).encode("utf-8")) + 1
                if size > self.settings.max_result_bytes:
                    cursor.cancel()
                    raise ResultLimitError("Result exceeds payload limit; select fewer columns")
                rows.append(values)
            return ResultTable(
                columns=columns,
                rows=rows,
                row_count=len(rows),
                elapsed_ms=int((time.monotonic() - started) * 1000),
            )
        except (pyodbc.Error, SQLAlchemyError) as exc:
            error = str(exc)
            if any(code in error for code in ("HYT00", "HYT01", "1222")):
                raise QueryTimeoutError("Query exceeded the database execution deadline") from exc
            raise ExecutionError("Database query failed; check the SQL and service health") from exc
        finally:
            failed = sys.exc_info()[0] is not None
            cleanup_failed = False
            try:
                if cursor is not None:
                    try:
                        cursor.close()
                    except (pyodbc.Error, SQLAlchemyError):
                        cleanup_failed = True
                if connection is not None:
                    try:
                        connection.rollback()
                    except (pyodbc.Error, SQLAlchemyError):
                        cleanup_failed = True
                    if cleanup_failed:
                        # A failed cancellation/rollback must not return a broken connection to the pool.
                        with suppress(pyodbc.Error, SQLAlchemyError):
                            connection.invalidate()
                    try:
                        connection.close()
                    except (pyodbc.Error, SQLAlchemyError):
                        cleanup_failed = True
            finally:
                self._slots.release()
            if cleanup_failed and not failed:
                raise ExecutionError(
                    "Database connection cleanup failed; retry after checking service health"
                )


class FabricSQLBackend:
    """Explicit opt-in capability boundary. M3 requires endpoint acceptance tests."""

    name = "fabric-sql-analytics"

    def execute(self, query: ValidatedQuery) -> ResultTable:
        raise ExecutionError(
            "Fabric execution is disabled until curated-table policy and dialect checks are approved"
        )
