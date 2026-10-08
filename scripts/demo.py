"""Real local SQL Server question -> proposal -> policy -> execution -> learning demonstration."""

import json
from pathlib import Path

from backend.agent.provider import MockProvider
from backend.agent.service import AgentService
from backend.config import Settings
from backend.database.connection import make_engine
from backend.database.executor import SQLServerBackend


def main() -> None:
    settings = Settings()
    db = SQLServerBackend(make_engine(settings), settings)
    try:
        db.verify_identity()
        answer = AgentService(MockProvider(), db).ask("Show total invoiced by region.", "local-demo")
        output = answer.model_dump_json(indent=2)
        Path("artifacts").mkdir(exist_ok=True)
        Path("artifacts/demo.json").write_text(output + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "question": "Show total invoiced by region.",
                    "result": answer.result.model_dump() if answer.result else None,
                    "artifact": "artifacts/demo.json",
                },
                indent=2,
            )
        )
    finally:
        db.engine.dispose()


if __name__ == "__main__":
    main()
