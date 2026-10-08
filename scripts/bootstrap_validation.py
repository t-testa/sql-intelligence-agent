"""Create a local-only edge fixture alongside (never overwrite) the existing demonstration database."""

from scripts.bootstrap_db import admin_connection, run_batches
from scripts.release_cases import edge_dataset

DATABASE = "SQLIntelligenceValidation"


def main() -> None:
    master = admin_connection()
    try:
        if master.execute("SELECT DB_ID(?)", DATABASE).fetchval() is not None:
            print("Local validation database already exists; run reference checks to verify its contents.")
            return
        master.execute("CREATE DATABASE SQLIntelligenceValidation")
    finally:
        master.close()
    conn = admin_connection(DATABASE)
    try:
        conn.autocommit = False
        run_batches(conn, "sql/schema/001_tables.sql")
        for name, rows in edge_dataset().items():
            columns = list(rows[0])
            sql = f"INSERT INTO ops.{name} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})"
            cursor = conn.cursor()
            cursor.executemany(sql, [tuple(row[column] for column in columns) for row in rows])
            cursor.close()
        run_batches(conn, "sql/views/001_reporting.sql")
        conn.execute("CREATE USER sql_runtime FOR LOGIN sql_runtime")
        run_batches(conn, "sql/schema/002_runtime_permissions.sql")
        conn.commit()
        print("Created local SQLIntelligenceValidation fixture with restricted runtime user; demo unchanged.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
