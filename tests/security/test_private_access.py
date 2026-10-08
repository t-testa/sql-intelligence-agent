"""Offline cryptographic and route tests; no Entra/SQL/model connection is used."""

import time
from types import SimpleNamespace
from unittest.mock import Mock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.agent.provider import MockProvider
from backend.api.main import create_app
from backend.config import Settings
from backend.contracts import ResultTable
from frontend.access import FrontendSettings, SignInRequired, authorization_headers, clear_user_state

TENANT = "11111111-1111-4111-8111-111111111111"
API = "22222222-2222-4222-8222-222222222222"
FRONTEND = "33333333-3333-4333-8333-333333333333"
OWNER = "44444444-4444-4444-8444-444444444444"
OTHER = "55555555-5555-4555-8555-555555555555"
ROUTES = [
    ("GET", "/catalog", None),
    ("POST", "/questions", {"question": "How many jobs are there?"}),
    ("POST", "/sql/validate", {"sql": "SELECT COUNT(*) AS N FROM reporting.vJobs"}),
    ("POST", "/practice", {"exercise_id": "jobs", "sql": "SELECT COUNT(*) AS N FROM reporting.vJobs"}),
    ("DELETE", f"/conversations/{OTHER}", None),
]


@pytest.fixture(autouse=True)
def isolate_local_token(monkeypatch):
    # SQL integration bootstrap loads the host .env. Cloud auth tests must not inherit its local token.
    monkeypatch.setenv("LOCAL_API_TOKEN", "")


def cloud_settings(**overrides):
    values = dict(
        app_env="cloud",
        auth_mode="entra",
        sql_managed_identity=True,
        sql_trust_certificate=False,
        entra_tenant_id=TENANT,
        entra_audience=API,
        entra_frontend_client_id=FRONTEND,
        entra_allowed_object_ids=[OWNER],
    )
    return Settings(_env_file=None, **(values | overrides))


@pytest.fixture(scope="module")
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def token(key, **updates):
    now = int(time.time())
    claims = (
        dict(
            aud=API,
            iss=f"https://login.microsoftonline.com/{TENANT}/v2.0",
            tid=TENANT,
            oid=OWNER,
            azp=FRONTEND,
            ver="2.0",
            scp="access_as_user",
            exp=now + 300,
            iat=now,
            nbf=now - 1,
        )
        | updates
    )
    return jwt.encode(claims, key, algorithm="RS256")


@pytest.fixture
def app(monkeypatch, signing_key):
    key_client = Mock()
    key_client.get_signing_key_from_jwt.return_value = SimpleNamespace(key=signing_key.public_key())
    monkeypatch.setattr(jwt, "PyJWKClient", Mock(return_value=key_client))
    settings = cloud_settings()
    backend = Mock()
    backend.name = "offline-fixture"
    backend.execute.return_value = ResultTable(columns=["JobCount"], rows=[[240]], row_count=1, elapsed_ms=1)
    provider = Mock(wraps=MockProvider())
    client = TestClient(create_app(settings, provider, backend))
    return client, settings, provider, backend


@pytest.mark.parametrize("method,path,body", ROUTES)
@pytest.mark.parametrize("identity", ["anonymous", "forged-header", "unapproved-user"])
def test_all_operations_authorize_before_model_or_database(app, signing_key, method, path, body, identity):
    client, _, provider, backend = app
    headers = {}
    if identity == "forged-header":
        headers = {"X-MS-CLIENT-PRINCIPAL-ID": OWNER, "X-MS-CLIENT-PRINCIPAL": "administrator"}
    elif identity == "unapproved-user":
        headers = {"Authorization": "Bearer " + token(signing_key, oid=OTHER)}
    response = client.request(method, path, json=body, headers=headers)
    assert response.status_code in {401, 403}
    provider.propose.assert_not_called()
    backend.execute.assert_not_called()


@pytest.mark.parametrize(
    "updates,status",
    [
        ({"aud": FRONTEND}, 401),  # ID token / token for the frontend is not an API token.
        ({"aud": OTHER}, 401),
        ({"iss": "https://attacker.invalid"}, 401),
        ({"tid": OTHER}, 403),
        ({"oid": OTHER}, 403),
        ({"oid": None}, 401),
        ({"azp": OTHER}, 403),
        ({"azp": None}, 403),
        ({"ver": "1.0"}, 403),
        ({"scp": "User.Read"}, 403),
        ({"scp": ["access_as_user"]}, 403),
        ({"scp": None, "roles": ["access_as_user"]}, 403),
        ({"idtyp": "app"}, 403),
        ({"exp": 0}, 401),
        ({"iat": 4102444800}, 401),
        ({"nbf": 4102444800}, 401),
    ],
)
def test_signed_but_invalid_claims_cannot_query(app, signing_key, updates, status):
    client, _, provider, backend = app
    response = client.post(
        "/questions",
        json={"question": "How many jobs are there?"},
        headers={"Authorization": "Bearer " + token(signing_key, **updates)},
    )
    assert response.status_code == status
    provider.propose.assert_not_called()
    backend.execute.assert_not_called()


def test_forged_signature_and_unsigned_token_rejected(app, signing_key):
    client, _, provider, backend = app
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    unsigned = jwt.encode(
        jwt.decode(token(signing_key), options={"verify_signature": False}), key="", algorithm="none"
    )
    for forged in (token(attacker_key), unsigned):
        assert client.get("/catalog", headers={"Authorization": "Bearer " + forged}).status_code == 401
    provider.propose.assert_not_called()
    backend.execute.assert_not_called()


def test_duplicate_bearer_headers_rejected(app, signing_key):
    client, _, _, backend = app
    header = ("Authorization", "Bearer " + token(signing_key))
    assert client.get("/catalog", headers=[header, header]).status_code == 401
    backend.execute.assert_not_called()


def test_delegated_frontend_token_reaches_independent_api_and_learning(app, signing_key):
    client, _, provider, backend = app
    settings = FrontendSettings(_env_file=None, app_env="cloud", api_url="https://api.internal.example")
    headers = authorization_headers(settings, {"X-MS-TOKEN-AAD-ACCESS-TOKEN": [token(signing_key)]})
    response = client.post("/questions", json={"question": "How many jobs are there?"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["result"]["rows"] == [[240]]
    assert response.json()["learning"]["exercise_id"] == "jobs"
    provider.propose.assert_called_once()
    backend.execute.assert_called_once()
    # Authentication never bypasses the existing practice SQL gateway.
    assert (
        client.post(
            "/practice", json={"exercise_id": "jobs", "sql": "DROP TABLE ops.Jobs"}, headers=headers
        ).status_code
        == 422
    )
    backend.execute.assert_called_once()


def test_expiry_renewal_and_revocation_are_checked_on_every_request(app, signing_key):
    client, settings, _, backend = app
    headers = {"Authorization": "Bearer " + token(signing_key)}
    assert (
        client.get("/catalog", headers={"Authorization": "Bearer " + token(signing_key, exp=0)}).status_code
        == 401
    )
    assert client.get("/catalog", headers=headers).status_code == 200
    settings.entra_allowed_object_ids = [OTHER]
    assert client.get("/catalog", headers=headers).status_code == 403
    settings.entra_allowed_object_ids = [OWNER]
    settings.application_access_enabled = False
    assert client.get("/catalog", headers=headers).status_code == 403
    backend.execute.assert_not_called()


def test_cloud_exposes_only_minimal_unauthenticated_liveness(app):
    client, _, provider, backend = app
    assert client.get("/health").json() == {"status": "ok"}
    for path in ("/docs", "/openapi.json", "/redoc"):
        assert client.get(path).status_code == 404
    provider.propose.assert_not_called()
    backend.execute.assert_not_called()


@pytest.mark.parametrize(
    "updates",
    [
        {"entra_frontend_client_id": ""},
        {"entra_frontend_client_id": API},
        {"entra_audience": "api://" + API},
        {"entra_allowed_object_ids": ["owner@example.invalid"]},
        {"entra_allowed_object_ids": []},
        {"auth_mode": "local"},
        {"sql_managed_identity": False},
        {"sql_trust_certificate": True},
        {"azure_openai_api_key": "secret-must-not-be-logged"},
    ],
)
def test_cloud_configuration_requires_explicit_identities(updates):
    with pytest.raises(ValidationError) as exc:
        cloud_settings(**updates)
    assert "secret-must-not-be-logged" not in str(exc.value)


@pytest.mark.parametrize(
    "incoming",
    [
        {},
        {"Authorization": ["Bearer a.b.c"]},
        {"X-MS-TOKEN-AAD-ID-TOKEN": ["a.b.c"]},
        {"X-MS-CLIENT-PRINCIPAL-ID": [OWNER]},
        {"X-MS-TOKEN-AAD-ACCESS-TOKEN": ["a.b.c", "a.b.c"]},
        {"X-MS-TOKEN-AAD-ACCESS-TOKEN": ["a.b.c\r\nInjected: true"]},
        {"X-MS-TOKEN-AAD-ACCESS-TOKEN": ["invalid"]},
        {"X-MS-TOKEN-AAD-ACCESS-TOKEN": ["a" * 16384 + ".b.c"]},
        {"X-MS-TOKEN-AAD-ACCESS-TOKEN": ["a.b.c"], "x-ms-token-aad-access-token": ["d.e.f"]},
    ],
)
def test_frontend_has_no_anonymous_or_shared_credential_fallback(incoming):
    settings = FrontendSettings(_env_file=None, app_env="cloud", api_url="https://api.internal.example")
    with pytest.raises(SignInRequired):
        authorization_headers(settings, incoming)


@pytest.mark.parametrize(
    "origin",
    [
        "http://api.example",
        "https://a:b@api.example",
        "https://api.example?secret=x",
        "https://api.example/path",
        "https://api.example:8000",
    ],
)
def test_cloud_frontend_requires_fixed_https_origin(origin):
    with pytest.raises(ValidationError):
        FrontendSettings(_env_file=None, app_env="cloud", api_url=origin)


def test_cloud_frontend_rejects_local_shared_token():
    with pytest.raises(ValidationError):
        FrontendSettings(
            _env_file=None, app_env="cloud", api_url="https://api.example", local_api_token="x" * 32
        )


def test_auth_failure_clears_results_and_learning_state():
    state = dict(
        history=["old result"],
        conversation_id="old",
        comparison_1="old",
        sql_1="old",
        chart_1=True,
        metric_1="old",
        preference="kept",
    )
    clear_user_state(state)
    assert state == {"preference": "kept"}


def test_local_regression_token_still_supported():
    settings = FrontendSettings(_env_file=None, local_api_token="x" * 32)
    assert authorization_headers(settings, {}) == {"Authorization": "Bearer " + "x" * 32}


@pytest.mark.parametrize("expired", [False, True])
def test_streamlit_cloud_auth_failure_clears_visible_state_without_inference(monkeypatch, expired):
    import httpx
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("APP_ENV", "cloud")
    monkeypatch.setenv("API_URL", "https://api.internal.example")
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.request.return_value = httpx.Response(401, text="<html>Unauthenticated</html>")
    constructor = Mock(return_value=client)
    monkeypatch.setattr(httpx, "Client", constructor)
    if expired:
        monkeypatch.setattr(
            "frontend.access.authorization_headers", lambda *_: {"Authorization": "Bearer a.b.c"}
        )
    page = AppTest.from_file("frontend/app.py")
    page.session_state["history"] = ["previous account result"]
    page.session_state["conversation_id"] = "previous account conversation"
    page.run(timeout=15)
    assert not page.exception
    assert page.error
    assert "history" not in page.session_state
    assert "conversation_id" not in page.session_state
    assert not page.chat_input
    if expired:
        assert constructor.call_args.kwargs["follow_redirects"] is False
        assert client.request.call_count == 1
        assert client.request.call_args.args[:2] == ("GET", "/catalog")
    else:
        constructor.assert_not_called()


def test_streamlit_late_revocation_removes_already_rendered_controls(monkeypatch):
    import httpx
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("APP_ENV", "cloud")
    monkeypatch.setenv("API_URL", "https://api.internal.example")
    monkeypatch.setattr("frontend.access.authorization_headers", lambda *_: {"Authorization": "Bearer a.b.c"})
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    catalog = {
        "mode": "mock",
        "examples": [{"question": f"Example {i}"} for i in range(10)],
        "metrics": {},
        "grains": {},
        "limits": {"rows": 500, "timeout_seconds": 10},
    }
    client.request.side_effect = lambda method, *_args, **_kwargs: (
        httpx.Response(200, json=catalog) if method == "GET" else httpx.Response(403, text="Denied")
    )
    monkeypatch.setattr(httpx, "Client", Mock(return_value=client))
    page = AppTest.from_file("frontend/app.py").run(timeout=15)
    assert not page.exception and page.chat_input
    page.chat_input[0].set_value("How many jobs are there?").run(timeout=15)
    assert not page.exception and page.error
    calls_after_denial = client.request.call_count
    page.run(timeout=15)
    assert not page.chat_input and not page.dataframe
    assert "history" not in page.session_state
    assert client.request.call_count == calls_after_denial
    assert sum(call.args[0] == "POST" for call in client.request.call_args_list) == 1
