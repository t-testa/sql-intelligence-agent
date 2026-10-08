import sys
from unittest.mock import Mock

import pytest

from backend.config import Settings
from backend.contracts import ResultTable
from scripts import verify_live


def configured():
    return Settings(
        _env_file=None,
        agent_mode="azure",
        azure_openai_endpoint="https://offline.invalid",
        azure_openai_deployment="test-deployment",
        azure_openai_api_key="do-not-print-this-key",
    )


@pytest.mark.parametrize("args", [[], ["--check-config"], ["--check-config", "--docker"]])
def test_config_checks_never_create_network_or_database_clients(monkeypatch, capsys, args):
    monkeypatch.setattr(sys, "argv", ["verify_live", *args])
    monkeypatch.setattr(verify_live, "Settings", lambda **kwargs: configured())
    network, database = (
        Mock(side_effect=AssertionError("network")),
        Mock(side_effect=AssertionError("database")),
    )
    monkeypatch.setattr(verify_live.httpx, "Client", network)
    monkeypatch.setattr(verify_live, "make_engine", database)
    assert verify_live.main() == 0
    assert not network.called and not database.called
    assert "do-not-print-this-key" not in capsys.readouterr().out


def test_docker_requires_key_but_host_can_use_identity(monkeypatch):
    settings = configured().model_copy(
        update={"azure_openai_api_key": Settings(_env_file=None).azure_openai_api_key}
    )
    monkeypatch.setattr(verify_live, "Settings", lambda **kwargs: settings)
    monkeypatch.setattr(sys, "argv", ["verify_live", "--docker"])
    assert verify_live.main() == 2
    monkeypatch.setattr(sys, "argv", ["verify_live", "--check-config"])
    assert verify_live.main() == 0


def test_cloud_opt_in_and_offline_flags_cannot_be_combined(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["verify_live", "--check-config", "--allow-cloud-call"])
    with pytest.raises(SystemExit) as error:
        verify_live.main()
    assert error.value.code == 2


def test_winner_oracle_handles_missing_invoices_and_equal_maxima():
    jobs = ResultTable(columns=["JobId"], rows=[[3], [2], [1]], row_count=3, elapsed_ms=0)
    invoices = ResultTable(
        columns=["InvoiceId", "JobId", "Amount"],
        rows=[[10, 1, "9.99"], [9, 1, "9.99"], [8, 1, "1.00"], [11, 2, "0.00"]],
        row_count=4,
        elapsed_ms=0,
    )
    assert verify_live.invoice_winners(jobs, invoices) == [[1, 9, "9.99"], [2, 11, "0.00"], [3, None, None]]
