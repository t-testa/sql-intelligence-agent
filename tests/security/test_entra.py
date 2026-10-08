import time
from types import SimpleNamespace
from unittest.mock import Mock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from starlette.requests import Request

from backend.config import Settings
from backend.security.auth import Authenticator


@pytest.fixture(scope="module")
def key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def authenticate(key, updates=None):
    now = int(time.time())
    claims = {
        "exp": now + 300,
        "iat": now,
        "nbf": now - 1,
        "aud": "api-id",
        "iss": "https://login.microsoftonline.com/tenant-id/v2.0",
        "tid": "tenant-id",
        "oid": "approved-user",
        "scp": "access_as_user",
    }
    claims.update(updates or {})
    settings = Settings(
        _env_file=None,
        auth_mode="entra",
        entra_tenant_id="tenant-id",
        entra_audience="api-id",
        entra_allowed_object_ids=["approved-user"],
    )
    auth = Authenticator(settings)
    auth.jwks = Mock()
    auth.jwks.get_signing_key_from_jwt.return_value = SimpleNamespace(key=key.public_key())
    token = jwt.encode(claims, key, algorithm="RS256")
    request = Request({"type": "http", "headers": [(b"authorization", f"Bearer {token}".encode())]})
    return auth.authenticate(request)


def test_verified_allowlisted_user(key):
    assert authenticate(key).subject == "approved-user"


@pytest.mark.parametrize(
    "updates,status",
    [
        ({"exp": 0}, 401),
        ({"aud": "wrong-api"}, 401),
        ({"iss": "https://attacker.invalid"}, 401),
        ({"tid": "other-tenant"}, 403),
        ({"oid": "unapproved-user"}, 403),
        ({"scp": "other_scope"}, 403),
        ({"scp": "", "roles": ["Admin"]}, 403),
    ],
)
def test_invalid_or_unauthorized_token(key, updates, status):
    with pytest.raises(HTTPException) as exc:
        authenticate(key, updates)
    assert exc.value.status_code == status
