import secrets
from dataclasses import dataclass
from typing import Any

import jwt
from fastapi import HTTPException, Request

from backend.config import Settings


@dataclass(frozen=True)
class Principal:
    subject: str


class Authenticator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if settings.auth_mode == "local" and len(settings.local_api_token.get_secret_value()) < 32:
            raise ValueError("Set a unique LOCAL_API_TOKEN of at least 32 characters")
        self.jwks: Any = None
        if settings.auth_mode == "entra":
            self.jwks = jwt.PyJWKClient(
                f"https://login.microsoftonline.com/{settings.entra_tenant_id}/discovery/v2.0/keys",
                cache_keys=True,
                timeout=5,
            )

    def authenticate(self, request: Request) -> Principal:
        if not self.settings.application_access_enabled:
            raise HTTPException(403, "Application access is disabled")
        if len(request.headers.getlist("Authorization")) != 1:
            raise HTTPException(401, "Exactly one bearer token is required")
        header = request.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token or len(token) > 16384:
            raise HTTPException(401, "A valid bearer token is required")
        if self.settings.auth_mode == "local":
            if not secrets.compare_digest(token, self.settings.local_api_token.get_secret_value()):
                raise HTTPException(401, "Invalid local bearer token")
            return Principal("local-operator")
        try:
            key = self.jwks.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.settings.entra_audience,
                issuer=f"https://login.microsoftonline.com/{self.settings.entra_tenant_id}/v2.0",
                options={"require": ["exp", "iat", "nbf", "aud", "iss", "oid", "tid"]},
            )
        except (jwt.PyJWTError, ValueError, TypeError) as exc:
            raise HTTPException(401, "Invalid Entra access token") from exc
        scope = claims.get("scp")
        if (
            claims["tid"] != self.settings.entra_tenant_id
            or claims["oid"] not in self.settings.entra_allowed_object_ids
            or not isinstance(scope, str)
            or self.settings.entra_required_scope not in scope.split()
            or claims.get("idtyp") == "app"
            or (
                self.settings.app_env == "cloud"
                and (
                    claims.get("ver") != "2.0" or claims.get("azp") != self.settings.entra_frontend_client_id
                )
            )
        ):
            raise HTTPException(403, "User or delegated scope is not authorized")
        return Principal(str(claims["oid"]))
