import json
from unittest.mock import Mock

import pytest

from scripts import azure_sql, local


@pytest.mark.parametrize("endpoint", ["ssh://remote", "tcp://127.0.0.1:2375", "https://remote"])
def test_launcher_refuses_nonlocal_docker_context(monkeypatch, endpoint):
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    engine = Mock(return_value=json.dumps([{"Endpoints": {"docker": {"Host": endpoint}}}]))
    monkeypatch.setattr(local, "docker", engine)
    with pytest.raises(RuntimeError, match="remote Docker engines are refused"):
        local.require_local_engine()
    assert engine.call_count == 1


def test_remote_context_cannot_be_hidden_by_docker_host(monkeypatch):
    monkeypatch.setenv("DOCKER_HOST", "unix:///var/run/docker.sock")
    monkeypatch.setattr(local, "docker", lambda _: '[{"Endpoints":{"docker":{"Host":"ssh://remote"}}}]')
    with pytest.raises(RuntimeError):
        local.require_local_engine()


def test_launcher_never_discloses_compose_error_credentials(monkeypatch):
    monkeypatch.setattr(
        local.subprocess, "run", Mock(return_value=Mock(returncode=1, stderr="SECRET-PASSWORD", stdout="KEY"))
    )
    with pytest.raises(RuntimeError) as error:
        local.docker(["compose", "config"])
    assert "SECRET-PASSWORD" not in str(error.value) and "KEY" not in str(error.value)


def local_configuration():
    return {
        "services": {
            "backend": {
                "environment": {
                    "AGENT_MODE": "mock",
                    "SQL_HOST": "sqlserver",
                    "LOCAL_API_TOKEN": "test-token",
                    "SQL_PASSWORD": "test-password",
                },
                "ports": [{"host_ip": "127.0.0.1"}],
            },
            "frontend": {"environment": {}},
        }
    }


@pytest.mark.parametrize("risk", ["public_port", "frontend_key", "admin_password", "cloud_sql", "no_auth"])
def test_launcher_rejects_security_regressions(monkeypatch, risk):
    config = local_configuration()
    backend = config["services"]["backend"]
    if risk == "public_port":
        backend["ports"][0]["host_ip"] = "0.0.0.0"
    elif risk == "frontend_key":
        config["services"]["frontend"]["environment"]["AZURE_OPENAI_API_KEY"] = "test-key"
    elif risk == "admin_password":
        backend["environment"]["SQL_ADMIN_PASSWORD"] = "test-password"
    elif risk == "cloud_sql":
        backend["environment"]["SQL_HOST"] = "cloud.database.windows.net"
    else:
        backend["environment"]["LOCAL_API_TOKEN"] = ""
    monkeypatch.setattr(local, "docker", lambda _: json.dumps(config))
    with pytest.raises(RuntimeError):
        local.check_configuration("mock")


def test_live_verification_requires_explicit_inference_opt_in(monkeypatch):
    monkeypatch.setattr("sys.argv", ["local", "verify-live"])
    engine = Mock()
    monkeypatch.setattr(local, "require_local_engine", engine)
    with pytest.raises(SystemExit):
        local.main()
    engine.assert_not_called()


@pytest.mark.parametrize("report,expected_code", [('{"status":"answered"}', 0), ("invalid JSON", 1)])
def test_tmpfs_evidence_is_recovered_by_exec_and_malformed_reports_fail(
    monkeypatch, tmp_path, report, expected_code
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(local, "ROOT", tmp_path)
    (tmp_path / ".env").write_text("")
    monkeypatch.setattr("sys.argv", ["local", "verify-live", "--allow-cloud-call"])
    monkeypatch.setattr(local, "require_local_engine", lambda: None)
    engine = Mock(side_effect=["", report])
    monkeypatch.setattr(local, "docker", engine)
    assert local.main() == expected_code
    files = list((tmp_path / "artifacts").glob("portable-live-*.json"))
    assert len(files) == (1 if expected_code == 0 else 0)
    if files:
        assert json.loads(files[0].read_text()) == {"status": "answered"}
    assert all("cp" not in call.args[0] for call in engine.call_args_list)


@pytest.mark.parametrize("host", ["localhost", "sqlserver", "sql.example", "x.database.windows.net;PWD=x"])
def test_azure_bootstrap_rejects_other_targets_and_connection_injection(host):
    with pytest.raises(ValueError):
        azure_sql.validate_target(host, "SQLIntelligence", "11111111-1111-4111-8111-111111111111")


def test_azure_bootstrap_plan_makes_no_connection(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "bootstrap",
            "--host",
            "test.database.windows.net",
            "--tenant-id",
            "11111111-1111-4111-8111-111111111111",
            "--runtime-client-id",
            "22222222-2222-4222-8222-222222222222",
            "--database",
            "SQLIntelligence",
        ],
    )
    connection = Mock()
    monkeypatch.setattr(azure_sql, "admin_connection", connection)
    assert azure_sql.main() == 0
    connection.assert_not_called()


@pytest.mark.parametrize("database,count", [("UnexpectedDatabase", 0), ("SQLIntelligence", 1)])
def test_bootstrap_never_overwrites_existing_or_wrong_database(database, count):
    connection = Mock()
    connection.execute.return_value.fetchval.side_effect = [database, count]
    with pytest.raises(ValueError):
        azure_sql.bootstrap(connection, "SQLIntelligence", "22222222-2222-4222-8222-222222222222")
    connection.commit.assert_not_called()
    connection.cursor.assert_not_called()


def test_bootstrap_failure_rolls_back_and_never_commits_partial_fixture(monkeypatch):
    connection = Mock()
    connection.execute.return_value.fetchval.side_effect = ["SQLIntelligence", 0]
    monkeypatch.setattr(azure_sql, "run_batches", Mock(side_effect=RuntimeError("DDL failed")))
    with pytest.raises(RuntimeError):
        azure_sql.bootstrap(connection, "SQLIntelligence", "22222222-2222-4222-8222-222222222222")
    connection.rollback.assert_called_once()
    connection.commit.assert_not_called()
