import json
from unittest.mock import Mock

import httpx
import pytest
from openai import APIStatusError, OpenAI
from pydantic import ValidationError

from backend.agent.conversation import ConversationTurn
from backend.agent.provider import AzureResponsesProvider, MockProvider, ModelError
from backend.agent.service import AgentService
from backend.config import Settings
from backend.contracts import Proposal, ResultTable
from tests.unseen import HIGHEST_QUESTION, UNSEEN


def response_body(proposal):
    return {
        "id": "resp_offline",
        "object": "response",
        "created_at": 1,
        "status": "completed",
        "model": "offline-deployment",
        "parallel_tool_calls": False,
        "output": [
            {
                "type": "function_call",
                "id": "fc_offline",
                "call_id": "call_offline",
                "name": "propose_query",
                "arguments": json.dumps(proposal),
            }
        ],
    }


@pytest.mark.parametrize("question,sql,parameters", UNSEEN)
def test_unseen_questions_use_actual_sdk_and_same_gateway_without_network(question, sql, parameters):
    captured = []

    def transport(request):
        captured.append(request)
        return httpx.Response(
            200,
            json=response_body(
                {
                    "action": "query",
                    "sql": sql,
                    "parameters": parameters,
                    "clarification": "",
                }
            ),
        )

    settings = Settings(_env_file=None, azure_openai_deployment="my-exact-deployment")
    with OpenAI(
        api_key="offline-test-key",
        base_url="https://offline.invalid/openai/v1/",
        http_client=httpx.Client(transport=httpx.MockTransport(transport)),
        max_retries=0,
    ) as sdk:
        backend = Mock()
        backend.execute.return_value = ResultTable(columns=["N"], rows=[[1]], row_count=1, elapsed_ms=0)
        answer = AgentService(AzureResponsesProvider(settings, client=sdk), backend).ask(question, "owner")
    assert answer.status == "answered"
    assert answer.learning.exercise_id is None
    assert MockProvider().propose(question).action == "clarify"
    assert len(captured) == 1
    request = captured[0]
    assert str(request.url) == "https://offline.invalid/openai/v1/responses"
    payload = json.loads(request.content)
    assert payload["model"] == "my-exact-deployment"
    assert payload["input"][-1]["content"] == question
    assert payload["store"] is False
    assert payload["tool_choice"]["name"] == "propose_query"
    assert payload["tools"][0]["parameters"]["additionalProperties"] is False
    assert payload["max_output_tokens"] == 4000
    query = backend.execute.call_args.args[0]
    assert query.views
    assert "@" not in query.bound_sql


def test_history_uses_user_and_assistant_roles_not_instructions():
    client = Mock()
    client.responses.create.return_value.status = "completed"
    proposal = Proposal(action="clarify", sql="", parameters=[], clarification="Contract value or invoiced?")
    client.responses.create.return_value.output = [
        Mock(type="function_call", **{"name": "propose_query", "arguments": proposal.model_dump_json()})
    ]
    # Mock's name argument is special; assign the function name explicitly.
    client.responses.create.return_value.output[0].name = "propose_query"
    history = (ConversationTurn.accepted("What is revenue in East?", proposal),)
    AzureResponsesProvider(Settings(_env_file=None), client).propose("Invoiced", history)
    request = client.responses.create.call_args.kwargs
    assert [message["role"] for message in request["input"]] == ["user", "assistant", "user"]
    assert request["input"][0]["content"] == "What is revenue in East?"
    assert "Contract value or invoiced?" in request["input"][1]["content"]
    assert "previous_response_id" not in request


@pytest.mark.parametrize("suffix", ["", "/", "/openai/v1", "/openai/v1/"])
def test_azure_endpoint_normalization_and_no_automatic_retries(suffix):
    settings = Settings(
        _env_file=None,
        agent_mode="azure",
        azure_openai_endpoint="https://example.openai.azure.com" + suffix,
        azure_openai_deployment="deployment",
        azure_openai_api_key="offline-key",
    )
    provider = AzureResponsesProvider(settings)
    try:
        assert str(provider.client.base_url) == "https://example.openai.azure.com/openai/v1/"
        assert provider.client.max_retries == 0
    finally:
        provider.client.close()


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://example.com",
        "https://example.com/openai/deployments/x",
        "https://user:secret@example.com",
        "https://example.com?api-key=secret",
        "https://example.com#fragment",
    ],
)
def test_malformed_endpoints_fail_before_a_request(endpoint):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            agent_mode="azure",
            azure_openai_endpoint=endpoint,
            azure_openai_deployment="deployment",
        )


@pytest.mark.parametrize(
    "status,hint", [(400, "strict"), (401, "key"), (403, "role"), (404, "deployment"), (429, "Quota")]
)
def test_provider_errors_are_actionable_and_sanitized(status, hint):
    client = Mock()
    response = httpx.Response(status, request=httpx.Request("POST", "https://offline.invalid"))
    client.responses.create.side_effect = APIStatusError(
        "secret-body", response=response, body={"secret": True}
    )
    provider = AzureResponsesProvider(Settings(_env_file=None), client)
    with pytest.raises(ModelError) as error:
        provider.propose(HIGHEST_QUESTION)
    assert hint in str(error.value)
    assert "secret" not in str(error.value)
