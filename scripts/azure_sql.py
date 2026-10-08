"""Explicit Azure SQL bootstrap for an EMPTY synthetic database; never used by the application."""

import argparse
import re
import struct
from typing import Any
from uuid import UUID

import pyodbc

from scripts.bootstrap_db import run_batches
from scripts.release_cases import edge_dataset
from scripts.seed_data import dataset

DATABASES = {"SQLIntelligence", "SQLIntelligenceValidation"}


def validate_target(host: str, database: str, tenant_id: str) -> None:
    UUID(tenant_id)
    if not re.fullmatch(r"[a-z0-9-]+\.database\.windows\.net", host) or database not in DATABASES:
        raise ValueError("Use an approved Azure SQL FQDN and a fixed synthetic database name")


def admin_connection(host: str, database: str, tenant_id: str) -> Any:
    from azure.identity import AzureCliCredential

    validate_target(host, database, tenant_id)
    # Uses an already authenticated, separately approved migration operator. No login or grants.
    with AzureCliCredential(tenant_id=tenant_id) as credential:
        token = credential.get_token("https://database.windows.net/.default").token.encode("utf-16-le")
    connection = pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={host},1433;DATABASE={database};"
        "Encrypt=yes;TrustServerCertificate=no",
        attrs_before={1256: struct.pack(f"<I{len(token)}s", len(token), token)},
        timeout=10,
    )
    connection.timeout = 30
    if connection.execute("SELECT CONVERT(int, SERVERPROPERTY('EngineEdition'))").fetchval() != 5:
        connection.close()
        raise ValueError("Only Azure SQL Database is supported by this bootstrap")
    return connection


def bootstrap(connection: Any, database: str, runtime_client_id: str) -> None:
    # Azure SQL SID syntax requires the CLIENT ID for a service principal/UAMI, not its object ID.
    sid = UUID(runtime_client_id).bytes_le.hex()
    if database not in DATABASES:
        raise ValueError("Unknown fixture database")
    if connection.execute("SELECT DB_NAME()").fetchval() != database:
        raise ValueError("Connected database differs from the approved target")
    if connection.execute("SELECT COUNT(*) FROM sys.tables WHERE is_ms_shipped=0").fetchval():
        raise ValueError("Database is not empty; existing data will never be overwritten")
    records = dataset() if database == "SQLIntelligence" else edge_dataset()
    try:
        connection.execute("SET XACT_ABORT ON")
        run_batches(connection, "sql/schema/001_tables.sql")
        for name, rows in records.items():
            columns = list(rows[0])
            cursor = connection.cursor()
            try:
                cursor.executemany(
                    f"INSERT INTO ops.{name} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                    [tuple(row[column] for column in columns) for row in rows],
                )
            finally:
                cursor.close()
        run_batches(connection, "sql/views/001_reporting.sql")
        # Explicit SID avoids a Graph directory-read grant to the SQL server identity.
        connection.execute(f"CREATE USER [sql_runtime] WITH SID = 0x{sid}, TYPE = E")
        run_batches(connection, "sql/schema/002_runtime_permissions.sql")
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument(
        "--runtime-client-id", required=True, help="Managed identity client ID for the SQL SID"
    )
    parser.add_argument("--database", choices=sorted(DATABASES), required=True)
    parser.add_argument("--apply", action="store_true", help="Only after explicit bootstrap/grant approval")
    args = parser.parse_args()
    try:
        validate_target(args.host, args.database, args.tenant_id)
        UUID(args.runtime_client_id)
        if not args.apply:
            print("Valid bootstrap inputs. No connection or changes made; --apply requires owner approval.")
            return 0
        connection = admin_connection(args.host, args.database, args.tenant_id)
        try:
            bootstrap(connection, args.database, args.runtime_client_id)
        finally:
            connection.close()
        print("Synthetic fixture and restricted runtime identity created. Run independent reference checks.")
        return 0
    except Exception as exc:
        print(f"Azure SQL bootstrap stopped ({type(exc).__name__}); raw connection output suppressed.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
