import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.agent.provider import AzureResponsesProvider, ModelError
from backend.config import Settings


def provider_client(arguments, name="propose_query", status="completed"):
    client = Mock()
    client.responses.create.return_value = SimpleNamespace(
        status=status,
        output=[SimpleNamespace(type="function_call", name=name, arguments=json.dumps(arguments))],
    )
    provider = AzureResponsesProvider(Settings(_env_file=None), client=client)
    return provider, client


def test_responses_api_contract_and_no_execution_tool():
    provider, client = provider_client(
        {"action": "query", "sql": "SELECT 1", "parameters": [], "clarification": ""}
    )
    assert provider.propose("test").sql == "SELECT 1"
    kwargs = client.responses.create.call_args.kwargs
    assert kwargs["tools"][0]["strict"] is True
    assert kwargs["tools"][0]["name"] == "propose_query"
    assert kwargs["store"] is False
    assert kwargs["parallel_tool_calls"] is False
    assert not client.chat.completions.create.called


@pytest.mark.parametrize(
    "name,status,arguments",
    [
        ("execute_sql", "completed", {}),
        ("propose_query", "incomplete", {}),
        ("propose_query", "completed", {"action": "query", "sql": "SELECT 1", "unsafe": True}),
    ],
)
def test_malformed_model_responses_fail_closed(name, status, arguments):
    provider, _ = provider_client(arguments, name, status)
    with pytest.raises(ModelError):
        provider.propose("test")
