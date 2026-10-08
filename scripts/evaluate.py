"""Run the mock execution benchmark and denial corpus; save exact outcomes without model scoring."""

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.agent.examples import EXAMPLES
from backend.agent.provider import MockProvider
from backend.agent.service import AgentService, canonical_rows
from backend.config import Settings
from backend.contracts import ResultTable
from backend.database.connection import make_engine
from backend.database.executor import SQLServerBackend
from backend.security.gateway import PolicyError, SQLGateway
from tests.security.attacks import ATTACKS


def main() -> None:
    expected = json.loads(Path("sql/seeds/expected_results.json").read_text(encoding="utf-8"))
    settings = Settings()
    db = SQLServerBackend(make_engine(settings), settings)
    outcomes = []
    try:
        db.verify_identity()
        service = AgentService(MockProvider(), db)
        for example in EXAMPLES:
            try:
                answer = service.ask(example.question, "evaluation")
                fixture = expected[example.id]
                golden = ResultTable(
                    columns=fixture["columns"],
                    rows=fixture["rows"],
                    row_count=len(fixture["rows"]),
                    elapsed_ms=0,
                )
                passed = answer.result is not None and (
                    canonical_rows(answer.result) == canonical_rows(golden)
                )
                outcomes.append({"id": example.id, "passed": passed})
            except Exception as exc:
                outcomes.append({"id": example.id, "passed": False, "error_type": type(exc).__name__})
    finally:
        db.engine.dispose()
    denied = 0
    for sql in ATTACKS:
        try:
            SQLGateway().validate(sql)
        except PolicyError:
            denied += 1
    passed_count = sum(1 for item in outcomes if item["passed"])
    report = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_mode": "deterministic_mock",
        "database": "SQL Server 2022 Developer",
        "questions": len(outcomes),
        "correct": passed_count,
        "execution_accuracy": passed_count / len(outcomes),
        "policy_attempts": len(ATTACKS),
        "policy_rejected": denied,
        "question_outcomes": outcomes,
        "limitations": [
            "Mock accuracy is not Azure model generalization accuracy.",
            "Only synthetic data and the reviewed SQL subset were evaluated.",
        ],
    }
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/evaluation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "question_outcomes"}, indent=2))
    if passed_count != len(outcomes) or denied != len(ATTACKS):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
