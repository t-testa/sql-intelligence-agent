import pytest

from backend.contracts import Parameter
from backend.security.gateway import PolicyError, SQLGateway
from tests.security.attacks import ATTACKS


@pytest.mark.parametrize("sql", ATTACKS)
def test_unauthorized_sql_is_rejected(sql):
    with pytest.raises(PolicyError):
        SQLGateway().validate(sql)


def test_parameter_value_cannot_become_sql():
    payload = "North'; DROP TABLE ops.Jobs; --"
    query = SQLGateway().validate(
        "SELECT JobId FROM reporting.vJobFinancials WHERE Region=@region",
        [Parameter(name="region", value=payload)],
    )
    assert payload not in query.bound_sql
    assert query.values == (payload,)
    assert "?" in query.bound_sql


def test_parameter_order_follows_generated_sql_not_tree_walk():
    query = SQLGateway().validate(
        "SELECT @label AS Label, JobId FROM reporting.vJobs "
        "WHERE Status=@status OR Status=@label ORDER BY JobId",
        [Parameter(name="status", value="Active"), Parameter(name="label", value="Completed")],
    )
    assert query.values == ("Completed", "Active", "Completed")


def test_parameter_like_literal_is_not_rewritten():
    query = SQLGateway().validate(
        "SELECT ':__sia_bind_0__ @region' AS Label FROM reporting.vCustomers WHERE Region=@region",
        [Parameter(name="region", value="North")],
    )
    assert "':__sia_bind_0__ @region'" in query.bound_sql
    assert query.values == ("North",)


@pytest.mark.parametrize(
    "bindings",
    [
        [Parameter(name="unused", value="North")],
        [Parameter(name="region", value="North"), Parameter(name="region", value="West")],
        [Parameter(name="region", value=float("nan"))],
        [Parameter(name="region", value=2**70)],
    ],
)
def test_invalid_bindings_rejected(bindings):
    with pytest.raises(PolicyError):
        SQLGateway().validate("SELECT JobId FROM reporting.vJobs WHERE Status=@region", bindings)


def test_aggregate_is_never_silently_top_limited():
    query = SQLGateway().validate("SELECT SUM(Amount) AS Total FROM reporting.vInvoices")
    assert "TOP" not in query.bound_sql.upper()


def test_case_and_bracketed_identifiers_allowed():
    SQLGateway().validate("SELECT [JobId] FROM [Reporting].[vJobs]")


def test_complexity_limit():
    sql = "SELECT JobId FROM reporting.vJobs WHERE " + " OR ".join("JobId=1" for _ in range(100))
    with pytest.raises(PolicyError):
        SQLGateway().validate(sql)
