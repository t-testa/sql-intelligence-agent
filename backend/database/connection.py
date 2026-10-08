import os
import struct
from typing import Any

from sqlalchemy import URL, Engine, create_engine, event

from backend.config import Settings


def make_engine(settings: Settings) -> Engine:
    query = {
        "driver": settings.sql_driver,
        "Encrypt": "yes",
        "TrustServerCertificate": "yes" if settings.sql_trust_certificate else "no",
    }
    url = URL.create(
        "mssql+pyodbc",
        host=settings.sql_host,
        port=settings.sql_port,
        database=settings.sql_database,
        username=None if settings.sql_managed_identity else settings.sql_username,
        password=None if settings.sql_managed_identity else settings.sql_password.get_secret_value(),
        query=query,
    )
    engine = create_engine(
        url,
        pool_size=settings.max_concurrent_queries,
        max_overflow=0,
        pool_timeout=1,
        pool_pre_ping=True,
        connect_args={"timeout": 5},
    )
    if settings.sql_managed_identity:
        from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

        credential = (
            ManagedIdentityCredential(client_id=os.environ.get("AZURE_CLIENT_ID"))
            if settings.app_env == "cloud"
            else DefaultAzureCredential()
        )

        @event.listens_for(engine, "do_connect")
        def provide_token(dialect: Any, conn_rec: Any, cargs: list[Any], cparams: dict[str, Any]) -> None:
            cargs[0] = cargs[0].replace(";Trusted_Connection=Yes", "")
            token = credential.get_token("https://database.windows.net/.default").token
            raw = token.encode("utf-16-le")
            cparams["attrs_before"] = {1256: struct.pack(f"<I{len(raw)}s", len(raw), raw)}

    @event.listens_for(engine, "connect")
    def set_query_timeout(connection: Any, record: Any) -> None:
        # pyodbc connection.timeout is SQL_ATTR_QUERY_TIMEOUT, not login timeout.
        connection.timeout = settings.query_timeout_seconds

    return engine
