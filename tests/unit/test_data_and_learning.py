import json
from decimal import Decimal

import pytest

from backend.agent.examples import BY_ID
from backend.agent.learning import explain, grounded_answer
from backend.agent.provider import MockProvider
from backend.agent.service import canonical_rows
from backend.contracts import ResultTable
from backend.security.gateway import SQLGateway
from scripts.build_fixtures import fixtures
from scripts.seed_data import dataset


def test_seed_is_deterministic_and_relational():
    data = dataset()
    assert data == dataset()
    assert sum(map(len, data.values())) == 1548
    customers = {c["CustomerId"] for c in data["Customers"]}
    jobs = {j["JobId"] for j in data["Jobs"]}
    assert all(j["CustomerId"] in customers for j in data["Jobs"])
    assert all(i["JobId"] in jobs for i in data["Invoices"] + data["Expenses"])
    assert len({(t["PeriodStart"], t["Region"]) for t in data["Targets"]}) == 48


def test_committed_fixtures_match_independent_decimal_oracle(expected):
    actual = json.loads(json.dumps(fixtures(), default=str))
    assert actual == expected
    assert set(expected) == set(BY_ID)
    assert Decimal(expected["invoiced"]["rows"][0][0]) - Decimal(
        expected["expenses"]["rows"][0][0]
    ) == Decimal(expected["margin"]["rows"][0][0])


@pytest.mark.parametrize(
    "example_id,concept",
    [
        ("rank_regions", "CTE"),
        ("rank_regions", "Window function"),
        ("above_average", "Subquery"),
        ("having", "HAVING"),
        ("jobs_region", "JOIN"),
        ("completed", "WHERE"),
        ("margin_pct", "NULLIF"),
        ("top_customers", "TOP"),
    ],
)
def test_learning_explains_actual_constructs(example_id, concept):
    e = BY_ID[example_id]
    lesson = explain(SQLGateway().validate(e.sql, e.bindings()))
    assert concept in lesson.concepts
    assert "one row" in lesson.grain


def test_ambiguous_revenue_requests_clarification():
    proposal = MockProvider().propose("What is our revenue?")
    assert proposal.action == "clarify"
    assert "contract value or total invoiced" in proposal.clarification
    assert proposal.sql == ""


def test_grounded_narrative_does_not_invent_numbers():
    result = ResultTable(columns=["Total"], rows=[["12.34"]], row_count=1, elapsed_ms=0)
    assert "12.34" in grounded_answer(result)


def test_multiset_comparison_preserves_duplicates():
    a = ResultTable(columns=["x"], rows=[[1], [1], [2]], row_count=3, elapsed_ms=0)
    b = ResultTable(columns=["x"], rows=[[1], [2], [2]], row_count=3, elapsed_ms=0)
    assert canonical_rows(a) != canonical_rows(b)


def test_financial_comparison_preserves_precision_beyond_decimal_context():
    def result(value):
        return ResultTable(columns=["amount"], rows=[[value]], row_count=1, elapsed_ms=0)

    assert canonical_rows(result("1234567890123456789012345678.01")) != canonical_rows(
        result("1234567890123456789012345678.02")
    )
    assert canonical_rows(result("1234567890123456789012345678.0100")) == canonical_rows(
        result("1234567890123456789012345678.01")
    )
