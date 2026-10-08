"""Read-only effective-permission checks using the actual cloud runtime managed identity."""

import json

import pyodbc

from backend.config import Settings
from backend.database.connection import make_engine
from backend.database.executor import SQLServerBackend


def main() -> int:
    settings = Settings()
    if settings.app_env != "cloud" or not settings.sql_managed_identity:
        raise ValueError("Run inside the approved cloud API container with its runtime identity")
    backend = SQLServerBackend(make_engine(settings), settings)
    checks: dict[str, bool] = {}
    try:
        backend.verify_identity()
        checks["runtime_identity"] = True
        connection = backend.engine.raw_connection()
        try:
            cursor = connection.cursor()
            for permission in ("CONTROL", "ALTER", "CREATE TABLE", "CREATE VIEW", "EXECUTE"):
                allowed = cursor.execute(
                    "SELECT HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', ?)", (permission,)
                ).fetchval()
                checks[f"database_denies_{permission}"] = allowed == 0
            for view in (
                "vCustomers",
                "vJobs",
                "vInvoices",
                "vExpenses",
                "vTargets",
                "vJobFinancials",
                "vMonthlyPerformance",
            ):
                for permission in ("SELECT", "INSERT", "UPDATE", "DELETE", "ALTER"):
                    allowed = cursor.execute(
                        "SELECT HAS_PERMS_BY_NAME(?, 'OBJECT', ?)", (f"reporting.{view}", permission)
                    ).fetchval()
                    checks[f"{view}_{permission}"] = allowed == (1 if permission == "SELECT" else 0)
            for table in ("Customers", "Jobs", "Invoices", "Expenses", "Targets"):
                for permission in ("SELECT", "INSERT", "UPDATE", "DELETE", "ALTER"):
                    allowed = cursor.execute(
                        "SELECT HAS_PERMS_BY_NAME(?, 'OBJECT', ?)", (f"ops.{table}", permission)
                    ).fetchval()
                    checks[f"{table}_denies_{permission}"] = allowed == 0
            try:
                cursor.execute("SELECT TOP (1) InternalNote FROM ops.Customers").fetchall()
                checks["actual_base_table_access_denied"] = False
            except pyodbc.Error as exc:
                checks["actual_base_table_access_denied"] = any("(229)" in str(arg) for arg in exc.args)
        finally:
            connection.rollback()
            connection.close()
    except Exception:
        checks["runtime_check_completed"] = False
    finally:
        backend.engine.dispose()
    print(json.dumps({"checks": checks, "passed": bool(checks) and all(checks.values())}, indent=2))
    return 0 if checks and all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
