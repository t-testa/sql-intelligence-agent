"""Privileged local bootstrap. Never import this module into the query agent."""

import os
import re
from pathlib import Path
from typing import Any

import pyodbc
from dotenv import load_dotenv

from scripts.seed_data import dataset


def admin_connection(database: str = "master") -> Any:
    load_dotenv()
    if os.environ.get("APP_ENV", "local") != "local":
        raise RuntimeError("This bootstrap is for the isolated local development container only")
    password = os.environ["SQL_ADMIN_PASSWORD"]
    host = os.environ.get("SQL_HOST", "localhost")
    if host not in {"localhost", "127.0.0.1", "sqlserver"}:
        raise RuntimeError("Local bootstrap refuses non-local SQL hosts")
    port = int(os.environ.get("SQL_PORT", "14339"))
    escaped = password.replace("}", "}}")
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={host},{port};"
        f"DATABASE={database};UID=sa;PWD={{{escaped}}};Encrypt=yes;TrustServerCertificate=yes",
        autocommit=True,
        timeout=5,
    )


def run_batches(conn: Any, path: str) -> None:
    for batch in re.split(r"(?im)^GO\s*$", Path(path).read_text(encoding="utf-8")):
        if batch.strip():
            conn.execute(batch)


def main() -> None:
    master = admin_connection()
    try:
        exists = master.execute("SELECT DB_ID('SQLIntelligence')").fetchval()
        if exists is not None:
            conn = admin_connection("SQLIntelligence")
            try:
                counts = {
                    name: conn.execute(f"SELECT COUNT(*) FROM ops.{name}").fetchval() for name in dataset()
                }
                if counts != {name: len(rows) for name, rows in dataset().items()}:
                    raise RuntimeError("Existing data differs; refusing to overwrite it")
                print("Existing seeded database detected; no changes made.", counts)
                return
            finally:
                conn.close()
        master.execute("CREATE DATABASE SQLIntelligence")
        password = os.environ["SQL_PASSWORD"]
        if not re.fullmatch(r"[A-Za-z0-9!_-]{20,128}", password):
            raise RuntimeError("Use a strong local runtime password with supported characters")
        master.execute(f"CREATE LOGIN sql_runtime WITH PASSWORD = '{password}', CHECK_POLICY=ON")
    finally:
        master.close()
    conn = admin_connection("SQLIntelligence")
    try:
        conn.autocommit = False
        run_batches(conn, "sql/schema/001_tables.sql")
        for name, rows in dataset().items():
            columns = list(rows[0])
            sql = f"INSERT INTO ops.{name} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})"
            cursor = conn.cursor()
            cursor.executemany(sql, [tuple(row[column] for column in columns) for row in rows])
            cursor.close()
        run_batches(conn, "sql/views/001_reporting.sql")
        conn.execute("CREATE USER sql_runtime FOR LOGIN sql_runtime")
        run_batches(conn, "sql/schema/002_runtime_permissions.sql")
        conn.commit()
        print("Seeded 1,548 records; approved reporting views and least-privilege runtime user ready.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
