"""Delegate login to ACA; forward only a user access token to the independently secured API."""

import re
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SignInRequired(RuntimeError):
    pass


class FrontendSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    app_env: Literal["local", "cloud"] = "local"
    api_url: str = "http://127.0.0.1:8000"
    local_api_token: SecretStr = SecretStr("")

    @model_validator(mode="after")
    def validate_origin(self) -> "FrontendSettings":
        origin = urlsplit(self.api_url)
        if (
            not origin.hostname
            or origin.username
            or origin.password
            or origin.query
            or origin.fragment
            or origin.path.rstrip("/")
            or origin.scheme not in {"http", "https"}
        ):
            raise ValueError("API_URL must be a configured origin without credentials or a path")
        if self.app_env == "cloud" and (
            origin.scheme != "https"
            or origin.port not in {None, 443}
            or self.local_api_token.get_secret_value()
        ):
            raise ValueError("Cloud frontend requires an HTTPS API origin and no shared local token")
        return self


def authorization_headers(
    settings: FrontendSettings, incoming: Mapping[str, Sequence[str]]
) -> dict[str, str]:
    if settings.app_env == "local":
        token = settings.local_api_token.get_secret_value()
        if len(token) < 32:
            raise SignInRequired("Local API authentication is not configured")
    else:
        # The platform supplies this header at the websocket handshake. Never trust identity-name,
        # principal JSON, ID tokens, browser Authorization, or a shared application credential.
        values = [
            value
            for name, entries in incoming.items()
            if name.lower() == "x-ms-token-aad-access-token"
            for value in entries
        ]
        if len(values) != 1:
            raise SignInRequired("Sign in with your approved Microsoft account")
        token = values[0]
        if len(token) > 16384 or not re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", token):
            raise SignInRequired("A valid delegated access token is required")
    # Presence/shape is not authorization: FastAPI verifies the JWT and current allowlist per request.
    return {"Authorization": f"Bearer {token}"}


def clear_user_state(state: MutableMapping[str, object]) -> None:
    """Clear displayed results and exercises after auth failure/account change, without retaining tokens."""
    for key in list(state):
        if key in {"history", "conversation_id"} or key.startswith(
            ("comparison_", "sql_", "chart_", "metric_")
        ):
            del state[key]
