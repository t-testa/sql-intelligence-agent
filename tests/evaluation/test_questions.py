import pytest

from backend.agent.examples import EXAMPLES
from backend.agent.provider import MockProvider
from backend.agent.service import AgentService, canonical_rows
from backend.contracts import ResultTable
from backend.security.gateway import SQLGateway


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.id)
def test_mock_proposal_is_validated(example):
    proposal = MockProvider().propose(example.question)
    assert proposal.action == "query"
    query = SQLGateway().validate(proposal.sql, proposal.parameters)
    assert query.views


@pytest.mark.integration
@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.id)
def test_execution_accuracy_against_independent_expected(example, sql_backend, expected):
    result = AgentService(MockProvider(), sql_backend).ask(example.question, "evaluation")
    fixture = expected[example.id]
    reference = ResultTable(
        columns=fixture["columns"],
        rows=fixture["rows"],
        row_count=len(fixture["rows"]),
        elapsed_ms=0,
    )
    assert result.result is not None
    assert [c.lower() for c in result.result.columns] == [c.lower() for c in reference.columns]
    assert canonical_rows(result.result) == canonical_rows(reference)


@pytest.mark.integration
@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.id)
def test_independent_reference_sql_matches_fixture(example, sql_backend, expected):
    fixture = expected[example.id]
    reference = sql_backend.execute(SQLGateway().validate(fixture["reference_sql"]))
    golden = ResultTable(
        columns=fixture["columns"],
        rows=fixture["rows"],
        row_count=len(fixture["rows"]),
        elapsed_ms=0,
    )
    assert canonical_rows(reference) == canonical_rows(golden)
