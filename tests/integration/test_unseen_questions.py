import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.agent.provider import AzureResponsesProvider
from backend.agent.service import AgentService, canonical_rows
from backend.config import Settings
from backend.contracts import Parameter, ResultTable
from backend.security.gateway import SQLGateway
from scripts.seed_data import dataset
from scripts.verify_live import invoice_winners, verify_answer
from tests.unseen import HIGHEST_SQL, UNSEEN

pytestmark = pytest.mark.integration


def expected_rows(case):
    data = dataset()
    if case == 0:
        winners = {}
        for invoice in sorted(data["Invoices"], key=lambda item: (-item["Amount"], item["InvoiceId"])):
            winners.setdefault(invoice["JobId"], invoice)
        return [
            [job["JobId"], winners[job["JobId"]]["InvoiceId"], str(winners[job["JobId"]]["Amount"])]
            for job in data["Jobs"]
        ]
    if case == 1:
        latest = {}
        for invoice in sorted(data["Invoices"], key=lambda item: (item["InvoiceDate"], item["InvoiceId"])):
            latest[invoice["JobId"]] = invoice
        return [
            [job_id, invoice["InvoiceId"], invoice["InvoiceDate"].isoformat()]
            for job_id, invoice in latest.items()
        ]
    if case == 2:
        rows = []
        for customer in data["Customers"]:
            jobs = [
                job
                for job in data["Jobs"]
                if job["CustomerId"] == customer["CustomerId"] and job["Status"] == "Completed"
            ]
            if len(jobs) > 2:
                rows.append(
                    [
                        customer["CustomerId"],
                        customer["CustomerName"],
                        len(jobs),
                        str(sum(job["ContractValue"] for job in jobs)),
                    ]
                )
        return rows
    rows = []
    for job in data["Jobs"]:
        invoices = [
            invoice
            for invoice in data["Invoices"]
            if invoice["JobId"] == job["JobId"] and invoice["InvoiceDate"].month == 1
        ]
        previous = None
        for invoice in sorted(invoices, key=lambda item: item["InvoiceId"]):
            rows.append(
                [
                    job["JobId"],
                    invoice["InvoiceId"],
                    str(invoice["Amount"]),
                    str(sum(item["Amount"] for item in invoices)),
                    previous,
                ]
            )
            previous = str(invoice["Amount"])
    return rows


@pytest.mark.parametrize("case", range(len(UNSEEN)))
def test_unseen_proposal_through_azure_adapter_gateway_and_real_sql_server(case, sql_backend):
    question, sql, parameters = UNSEEN[case]
    client = Mock()
    client.responses.create.return_value = SimpleNamespace(
        status="completed",
        output=[
            SimpleNamespace(
                type="function_call",
                name="propose_query",
                arguments=json.dumps(
                    {
                        "action": "query",
                        "sql": sql,
                        "parameters": parameters,
                        "clarification": "",
                    }
                ),
            )
        ],
    )
    answer = AgentService(AzureResponsesProvider(Settings(_env_file=None), client), sql_backend).ask(
        question, "test"
    )
    expected = ResultTable(
        columns=answer.result.columns,
        rows=expected_rows(case),
        row_count=len(expected_rows(case)),
        elapsed_ms=0,
    )
    assert canonical_rows(answer.result) == canonical_rows(expected)
    if case == 0:
        verify_answer(answer.model_dump(), expected.rows)
        # Planned jobs have two zero-amount invoices: select the lower InvoiceID.
        row = next(row for row in answer.result.rows if row[0] == 12)
        assert row[:2] == [12, 23] and Decimal(row[2]) == 0


def test_jobs_without_qualifying_invoices_survive_left_join(sql_backend):
    sql = HIGHEST_SQL.replace("FROM reporting.vInvoices", "FROM reporting.vInvoices WHERE Amount > @floor")
    result = sql_backend.execute(SQLGateway().validate(sql, [Parameter(name="floor", value=1000000)]))
    assert result.rows == [[job["JobId"], None, None] for job in dataset()["Jobs"]]


def test_live_verification_oracle_reads_runtime_views(sql_backend):
    gateway = SQLGateway()
    jobs = sql_backend.execute(gateway.validate("SELECT JobId FROM reporting.vJobs"))
    invoices = sql_backend.execute(
        gateway.validate("SELECT InvoiceId, JobId, Amount FROM reporting.vInvoices")
    )
    assert invoice_winners(jobs, invoices) == expected_rows(0)
