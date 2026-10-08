import pytest
from pydantic import ValidationError

from backend.config import Settings


@pytest.mark.parametrize(
    "overrides",
    [
        {"app_env": "cloud"},
        {"auth_mode": "entra"},
        {
            "app_env": "cloud",
            "auth_mode": "entra",
            "sql_managed_identity": True,
            "entra_tenant_id": "tenant",
            "entra_audience": "aud",
            "entra_allowed_object_ids": ["user"],
        },
    ],
)
def test_cloud_defaults_fail_closed(overrides):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **overrides)
