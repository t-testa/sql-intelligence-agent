import pytest

from backend.security.gateway import PolicyError, SQLGateway
from tests.unseen import HIGHEST_SQL


@pytest.mark.parametrize(
    "before,after",
    [
        ("ROW_NUMBER()", "RANK()"),
        ("ROW_NUMBER()", "DENSE_RANK()"),
        ("PARTITION BY JobId", "PARTITION BY InvoiceId"),
        ("PARTITION BY JobId", "PARTITION BY JobId, Amount"),
        ("SELECT JobId,", "SELECT InvoiceId AS JobId,"),
        ("AND r.rn = 1", "OR r.rn = 1"),
        ("AND r.rn = 1", ""),
        ("r.rn = 1", "r.rn > 1"),
        ("r.rn = 1", "r.rn = 2"),
        ("j.JobId = r.JobId", "j.JobId = j.JobId"),
        ("LEFT JOIN", "CROSS JOIN"),
        ("LEFT JOIN", "RIGHT JOIN"),
        ("Amount DESC, InvoiceId ASC", "Amount DESC"),
        ("FROM reporting.vInvoices", "FROM ops.Invoices"),
        ("r.rn = 1", "r.rn = 1 AND j.JobId > 0"),
    ],
)
def test_ranked_join_does_not_authorize_fanout_or_key_spoofing(before, after):
    with pytest.raises(PolicyError):
        SQLGateway().validate(HIGHEST_SQL.replace(before, after))


def test_equivalent_reversed_key_equalities_are_accepted():
    sql = HIGHEST_SQL.replace("j.JobId = r.JobId AND r.rn = 1", "1 = r.rn AND r.JobId = j.JobId")
    assert SQLGateway().validate(sql).views == ("vInvoices", "vJobs")


def test_parenthesized_join_predicates_preserve_the_cardinality_proof():
    sql = HIGHEST_SQL.replace("j.JobId = r.JobId AND r.rn = 1", "((j.JobId = r.JobId) AND (r.rn = 1))")
    assert SQLGateway().validate(sql).views == ("vInvoices", "vJobs")
