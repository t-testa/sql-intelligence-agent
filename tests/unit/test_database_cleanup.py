from unittest.mock import Mock

import pyodbc
import pytest

from backend.config import Settings
from backend.database.executor import ExecutionError, QueryTimeoutError, SQLServerBackend
from backend.security.gateway import SQLGateway


def test_broken_rollback_preserves_sanitized_timeout_and_releases_capacity():
    connection = Mock()
    cursor = connection.cursor.return_value
    cursor.execute.side_effect = [None, pyodbc.OperationalError("HYT00", "private driver details")]
    connection.rollback.side_effect = pyodbc.OperationalError("08S01", "private cleanup details")
    engine = Mock()
    engine.raw_connection.return_value = connection
    db = SQLServerBackend(engine, Settings(_env_file=None, max_concurrent_queries=1))
    with pytest.raises(QueryTimeoutError, match="database execution deadline") as error:
        db.execute(SQLGateway().validate("SELECT JobId FROM reporting.vJobs"))
    assert "private" not in str(error.value)
    connection.invalidate.assert_called_once()
    connection.close.assert_called_once()
    assert db._slots.acquire(blocking=False)


def test_successful_query_with_failed_cleanup_is_not_reported_as_success():
    connection = Mock()
    cursor = connection.cursor.return_value
    cursor.description = [("JobId",)]
    cursor.fetchone.return_value = None
    connection.rollback.side_effect = pyodbc.OperationalError("08S01", "private cleanup details")
    engine = Mock()
    engine.raw_connection.return_value = connection
    db = SQLServerBackend(engine, Settings(_env_file=None))
    with pytest.raises(ExecutionError, match="connection cleanup failed"):
        db.execute(SQLGateway().validate("SELECT JobId FROM reporting.vJobs"))
    connection.invalidate.assert_called_once()
