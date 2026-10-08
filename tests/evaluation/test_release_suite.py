import hashlib
import json
from pathlib import Path

import pytest

from backend.config import Settings
from backend.contracts import Proposal, ResultTable
from backend.database.connection import make_engine
from backend.database.executor import SQLServerBackend, scalar
from scripts.bootstrap_db import admin_connection
from scripts.release_cases import cases
from scripts.release_eval import assess, check_narrative, compare

CASES = json.loads(Path("evaluation/cases.json").read_text(encoding="utf-8"))


def test_frozen_release_cases_match_independent_generator():
    assert json.loads(json.dumps(cases(), default=str)) == CASES
    assert sum(case["expect"] == "query" for case in CASES) >= 50
    assert len({case["id"] for case in CASES}) == len(CASES)


@pytest.mark.integration
@pytest.mark.parametrize("case", [c for c in CASES if c["expect"] == "query"], ids=lambda c: c["id"])
def test_release_reference_sql_matches_frozen_fixture(case, sql_backend):
    database = "SQLIntelligenceValidation" if case["fixture"] == "edge" else "SQLIntelligence"
    conn = admin_connection(database)
    try:
        cursor = conn.execute(case["reference_sql"])
        rows = [[scalar(value) for value in row] for row in cursor.fetchall()]
        result = ResultTable(
            columns=[c[0] for c in cursor.description], rows=rows, row_count=len(rows), elapsed_ms=0
        )
    finally:
        conn.close()
    assert compare(case, result) == []


def test_grader_detects_precision_null_order_and_duplicate_errors():
    case = {"columns": ["Amount"], "rows": [["1.00"], ["2.00"], [None]], "ordered": True}

    def result(rows):
        return ResultTable(columns=["Amount"], rows=rows, row_count=len(rows), elapsed_ms=0)

    assert compare(case, result([["1.001"], ["2.00"], [None]]))
    assert compare(case, result([["1.00"], ["2.00"], [0]]))
    assert compare(case, result([[None], ["2.00"], ["1.00"]])) == ["ordering"]
    assert compare(case, result([["1.00"], ["1.00"], [None]]))


def test_narrative_checker_rejects_invented_facts():
    result = ResultTable(columns=["Total"], rows=[["12.34"]], row_count=1, elapsed_ms=0)
    assert not check_narrative(result, "The total was 99.99, up 12% year over year.")


@pytest.mark.integration
def test_recorded_live_cases_replay_without_cloud(sql_backend):
    path = Path("evaluation/recordings/accepted.json")
    if not path.exists():
        pytest.fail("Release recording is missing")
    recording = json.loads(path.read_text(encoding="utf-8"))
    assert recording["complete"] and recording["failed"] == 0
    assert recording["suite_sha256"] == hashlib.sha256(Path("evaluation/cases.json").read_bytes()).hexdigest()
    records = {item["id"]: item for item in recording["outcomes"]}
    assert set(records) == {case["id"] for case in CASES}
    settings = Settings(sql_database="SQLIntelligenceValidation")
    edge = SQLServerBackend(make_engine(settings), settings)
    try:
        edge.verify_identity()
        for case in CASES:
            record = records[case["id"]]
            assert record["receipt"]["deployment_requested"] == "sql-agent-model"
            assert record["receipt"]["status"] == "completed"
            assert record["receipt"]["response_id"] and not record["failures"]
            outcome = assess(
                case,
                Proposal.model_validate(records[case["id"]]["proposal"]),
                edge if case["fixture"] == "edge" else sql_backend,
            )
            assert not outcome["failures"], (case["id"], outcome["failures"])
    finally:
        edge.engine.dispose()
