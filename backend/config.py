from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    app_env: Literal["local", "cloud"] = "local"
    auth_mode: Literal["local", "entra"] = "local"
    local_api_token: SecretStr = SecretStr("")
    agent_mode: Literal["mock", "azure"] = "mock"
    sql_host: str = "127.0.0.1"
    sql_port: int = 14339
    sql_database: str = "SQLIntelligence"
    sql_username: str = "sql_runtime"
    sql_password: SecretStr = SecretStr("")
    sql_driver: str = "ODBC Driver 18 for SQL Server"
    sql_trust_certificate: bool = True
    sql_managed_identity: bool = False
    sql_expected_principal: str = "sql_runtime"
    query_timeout_seconds: int = Field(default=10, ge=1, le=60)
    max_concurrent_queries: int = Field(default=3, ge=1, le=10)
    max_result_rows: int = Field(default=500, ge=1, le=2000)
    max_result_bytes: int = Field(default=262144, ge=1024, le=1048576)
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_key: SecretStr = SecretStr("")
    azure_openai_token_scope: str = "https://ai.azure.com/.default"
    azure_openai_timeout_seconds: int = Field(default=30, ge=5, le=45)
    azure_openai_max_output_tokens: int = Field(default=4000, ge=1000, le=8000)
    azure_openai_requests_per_minute: int = Field(default=6, ge=1, le=100)
    azure_openai_tokens_per_minute: int = Field(default=18000, ge=1000, le=1000000)
    azure_openai_daily_request_limit: int = Field(default=100, ge=1, le=10000)
    entra_tenant_id: str = ""
    entra_audience: str = ""
    entra_allowed_object_ids: list[str] = Field(default_factory=list)
    entra_required_scope: str = "access_as_user"
    entra_frontend_client_id: str = ""
    application_access_enabled: bool = True

    @model_validator(mode="after")
    def validate_auth(self) -> "Settings":
        if self.app_env == "cloud":
            if self.auth_mode != "entra" or not self.sql_managed_identity:
                raise ValueError("Cloud requires Entra authentication and SQL managed identity")
            if self.sql_trust_certificate or self.azure_openai_api_key.get_secret_value():
                raise ValueError("Cloud requires certificate verification and Azure identity")
            try:
                for identifier in [
                    self.entra_tenant_id,
                    self.entra_audience,
                    self.entra_frontend_client_id,
                    *self.entra_allowed_object_ids,
                ]:
                    UUID(identifier)
            except ValueError as exc:
                raise ValueError(
                    "Cloud requires explicit Entra tenant, API/client and user object UUIDs"
                ) from exc
            if self.entra_audience == self.entra_frontend_client_id:
                raise ValueError("Use separate Entra registrations for the frontend and API")
        if self.auth_mode == "entra" and not (
            self.entra_tenant_id and self.entra_audience and self.entra_allowed_object_ids
        ):
            raise ValueError("Entra requires tenant, audience and an explicit user object-ID allowlist")
        if self.agent_mode == "azure" and not (
            self.azure_openai_endpoint.startswith("https://") and self.azure_openai_deployment
        ):
            raise ValueError("Azure mode requires an HTTPS endpoint and deployment name")
        if self.azure_openai_endpoint:
            endpoint = urlsplit(self.azure_openai_endpoint)
            if (
                endpoint.scheme != "https"
                or not endpoint.hostname
                or endpoint.username
                or endpoint.password
                or endpoint.query
                or endpoint.fragment
                or endpoint.path.rstrip("/") not in {"", "/openai/v1"}
            ):
                raise ValueError("Azure endpoint must be an HTTPS resource origin or /openai/v1/ base URL")
            self.azure_openai_endpoint = f"https://{endpoint.netloc}"
        return self
