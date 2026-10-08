"""Metadata gates must reject broad access and missing approval, without cloud calls."""

import copy

import pytest

from scripts.private_preflight import (
    approved_identity_config,
    initial_identity_config,
    registration_checks,
    single_owner_assignments,
)
from tests.security.test_private_access import API, FRONTEND, OTHER, OWNER, TENANT

CONFIG = {
    "tenant_id": TENANT,
    "approved_user_object_id": OWNER,
    "api_client_id": API,
    "frontend_client_id": FRONTEND,
    "owner_approval_recorded": True,
    "private_redirect_uri": "https://private.example/.auth/login/aad/callback",
}


def test_unassigned_callback_allows_metadata_inspection_but_never_passes_release_gate():
    pending = CONFIG | {"private_redirect_uri": ""}
    assert approved_identity_config(pending)
    assert not initial_identity_config(pending)
    assert not approved_identity_config(pending | {"owner_approval_recorded": False})
    assert not approved_identity_config(pending | {"frontend_client_id": API})


@pytest.mark.parametrize(
    "updates",
    [
        {"owner_approval_recorded": False},
        {"approved_user_object_id": ""},
        {"approved_user_object_id": "someone@example.invalid"},
        {"frontend_client_id": API},
        {"private_redirect_uri": "http://private.example/.auth/login/aad/callback"},
        {"private_redirect_uri": "https://private.example/.auth/login/aad/callback?redirect=elsewhere"},
    ],
)
def test_identity_preflight_never_infers_owner_approval(updates):
    assert initial_identity_config(CONFIG)
    assert not initial_identity_config(CONFIG | updates)


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [{"principalId": OWNER, "principalType": "Group"}],
        [{"principalId": OWNER, "principalType": "User"}, {"principalId": OTHER, "principalType": "User"}],
    ],
)
def test_assignment_gate_rejects_missing_or_broad_access(rows):
    assert not single_owner_assignments({"value": rows}, OWNER)


def test_assignment_gate_does_not_hide_pagination():
    result = {"value": [{"principalId": OWNER, "principalType": "User"}]}
    assert single_owner_assignments(result, OWNER)
    assert not single_owner_assignments(result | {"@odata.nextLink": "more"}, OWNER)


def test_registration_gate_checks_scope_callback_and_tenant():
    api = {
        "signInAudience": "AzureADMyOrg",
        "identifierUris": [f"api://{API}"],
        "api": {
            "requestedAccessTokenVersion": 2,
            "oauth2PermissionScopes": [{"id": OTHER, "value": "access_as_user", "isEnabled": True}],
        },
    }
    frontend = {
        "signInAudience": "AzureADMyOrg",
        "web": {
            "redirectUris": [CONFIG["private_redirect_uri"]],
            "implicitGrantSettings": {"enableIdTokenIssuance": True},
        },
        "requiredResourceAccess": [
            {"resourceAppId": API, "resourceAccess": [{"id": OTHER, "type": "Scope"}]}
        ],
    }
    assert all(registration_checks(CONFIG, api, frontend).values())
    changed = copy.deepcopy(frontend)
    changed["web"]["implicitGrantSettings"]["enableIdTokenIssuance"] = False
    assert not registration_checks(CONFIG, api, changed)["easy_auth_id_token_issuance"]
    changed = copy.deepcopy(frontend)
    changed["signInAudience"] = "AzureADMultipleOrgs"
    assert not registration_checks(CONFIG, api, changed)["single_tenant_registrations"]
    changed = copy.deepcopy(frontend)
    changed["web"]["redirectUris"].append("https://unapproved.example/callback")
    assert not registration_checks(CONFIG, api, changed)["exact_private_callback"]
    changed = copy.deepcopy(frontend)
    changed["requiredResourceAccess"][0]["resourceAccess"][0]["type"] = "Role"
    assert not registration_checks(CONFIG, api, changed)["frontend_delegated_permission"]
