import json
import os
from pathlib import Path

import pytest

from backend.config import Settings
from backend.database.connection import make_engine
from backend.database.executor import SQLServerBackend


@pytest.fixture(autouse=True)
def no_live_credentials_in_regressions(monkeypatch):
    """Tests never inherit live inference credentials, even if local .env is configured."""
    for key, value in {
        "AGENT_MODE": "mock",
        "AZURE_OPENAI_ENDPOINT": "",
        "AZURE_OPENAI_DEPLOYMENT": "",
        "AZURE_OPENAI_API_KEY": "",
        "AZURE_OPENAI_MAX_OUTPUT_TOKENS": "4000",
    }.items():
        monkeypatch.setenv(key, value)


@pytest.fixture(scope="session")
def expected():
    return json.loads(Path("sql/seeds/expected_results.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def sql_backend():
    if os.environ.get("RUN_SQL_INTEGRATION") != "1":
        pytest.skip("Set RUN_SQL_INTEGRATION=1 to test against the isolated SQL Server")
    settings = Settings()
    backend = SQLServerBackend(make_engine(settings), settings)
    backend.verify_identity()
    yield backend
    backend.engine.dispose()
