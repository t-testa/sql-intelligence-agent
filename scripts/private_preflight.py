"""Read-only identity/repository preflight. No grants, login, deployment or inference operations.

Copy the example to ignored .local/private-preflight.json. Explicit owner approval is a human
prerequisite, never inferred from the Azure CLI's signed-in identity. Raw CLI responses stay in memory.
This checks metadata, not an actual Container Apps login or SQL network/permission acceptance.
"""

import argparse
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID


def read_cli(command: str, *args: str) -> Any:
    executable = shutil.which(command)
    if not executable:
        raise RuntimeError("Required read-only CLI is unavailable")
    result = subprocess.run([executable, *args], capture_output=True, text=True, timeout=45)
    if result.returncode:
        # Never surface CLI stderr, tokens, object details or login cache paths.
        raise RuntimeError("Read-only metadata request failed; verify login and read permissions")
    return json.loads(result.stdout)


def approved_identity_config(config: dict[str, Any]) -> bool:
    """Permit metadata inspection before Azure has assigned the private callback hostname."""
    try:
        for name in ("tenant_id", "approved_user_object_id", "api_client_id", "frontend_client_id"):
            UUID(config[name])
        return bool(
            config.get("owner_approval_recorded") is True
            and config["api_client_id"] != config["frontend_client_id"]
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def initial_identity_config(config: dict[str, Any]) -> bool:
    try:
        redirect = urlsplit(config["private_redirect_uri"])
        return bool(
            approved_identity_config(config)
            and redirect.scheme == "https"
            and redirect.hostname
            and not redirect.username
            and not redirect.password
            and not redirect.query
            and not redirect.fragment
            and redirect.path == "/.auth/login/aad/callback"
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def single_owner_assignments(assignments: dict[str, Any], owner: str) -> bool:
    values = assignments.get("value", [])
    return (
        bool(values)
        and not assignments.get("@odata.nextLink")
        and all(row.get("principalId") == owner and row.get("principalType") == "User" for row in values)
    )


def registration_checks(
    config: dict[str, Any], api: dict[str, Any], frontend: dict[str, Any]
) -> dict[str, bool]:
    scopes = [
        s
        for s in api.get("api", {}).get("oauth2PermissionScopes", [])
        if s.get("value") == "access_as_user" and s.get("isEnabled") is True
    ]
    scope_ids = {s["id"] for s in scopes}
    permissions = frontend.get("requiredResourceAccess", [])
    delegated = any(
        p.get("resourceAppId") == config["api_client_id"]
        and any(a.get("id") in scope_ids and a.get("type") == "Scope" for a in p.get("resourceAccess", []))
        for p in permissions
    )
    web = frontend.get("web", {})
    return {
        "single_tenant_registrations": all(
            a.get("signInAudience") == "AzureADMyOrg" for a in (api, frontend)
        ),
        "api_v2_delegated_scope": api.get("api", {}).get("requestedAccessTokenVersion") == 2
        and len(scopes) == 1
        and f"api://{config['api_client_id']}" in api.get("identifierUris", []),
        "frontend_delegated_permission": delegated,
        "exact_private_callback": web.get("redirectUris") == [config["private_redirect_uri"]],
        "easy_auth_id_token_issuance": web.get("implicitGrantSettings", {}).get("enableIdTokenIssuance")
        is True,
        "no_public_client_flows": not frontend.get("isFallbackPublicClient")
        and not frontend.get("publicClient", {}).get("redirectUris")
        and not frontend.get("spa", {}).get("redirectUris")
        and not web.get("implicitGrantSettings", {}).get("enableAccessTokenIssuance"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(".local/private-preflight.json"))
    parser.add_argument("--read-cloud", action="store_true", help="Read Azure/Graph and GitHub metadata only")
    parser.add_argument("--output", type=Path, default=Path("artifacts/private-preflight.json"))
    args = parser.parse_args()
    checks: list[dict[str, str]] = []

    def record(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "status": "pass" if passed else "blocked", "detail": detail})

    try:
        config = json.loads(args.config.read_text(encoding="utf-8")) if args.config.exists() else {}
        configured = isinstance(config, dict) and initial_identity_config(config)
        record(
            "explicit_owner_and_registration_configuration",
            configured,
            "Requires approved tenant/user IDs, separate application IDs and private callback.",
        )
        repo = config.get("github_repository", "") if isinstance(config, dict) else ""
        repo_configured = isinstance(repo, str) and re.fullmatch(r"[\w.-]+/[\w.-]+", repo) is not None
        record("repository_identified", repo_configured, "Use the exact private owner/repository name.")
        if not args.read_cloud:
            record("live_identity_and_repository_metadata", False, "Read-only cloud checks have not run.")
        else:
            if repo_configured:
                try:
                    repository = read_cli("gh", "api", f"repos/{repo}")
                    record(
                        "github_source_private",
                        repository.get("private") is True and repository.get("visibility") == "private",
                    )
                    record("github_pages_disabled", repository.get("has_pages") is False)
                except (RuntimeError, subprocess.SubprocessError, ValueError):
                    record(
                        "github_source_private",
                        False,
                        "GitHub CLI unavailable/unauthorized; verify through the connected GitHub tool.",
                    )
            if isinstance(config, dict) and approved_identity_config(config):
                try:
                    account = read_cli("az", "account", "show", "--output", "json")
                    if account.get("tenantId") != config["tenant_id"]:
                        raise RuntimeError("Wrong tenant")
                    record("azure_cli_approved_tenant", True)
                    operator = read_cli("az", "ad", "signed-in-user", "show", "--output", "json")
                    if operator.get("id") != config["approved_user_object_id"]:
                        raise RuntimeError("Signed-in operator is not the approved owner")
                    record("azure_cli_approved_owner", True)
                    api = read_cli(
                        "az", "ad", "app", "show", "--id", config["api_client_id"], "--output", "json"
                    )
                    frontend = read_cli(
                        "az", "ad", "app", "show", "--id", config["frontend_client_id"], "--output", "json"
                    )
                    for name, passed in registration_checks(config, api, frontend).items():
                        record(name, passed)
                    user = read_cli(
                        "az",
                        "rest",
                        "--method",
                        "get",
                        "--url",
                        "https://graph.microsoft.com/v1.0/users/"
                        + config["approved_user_object_id"]
                        + "?$select=id,accountEnabled",
                        "--output",
                        "json",
                    )
                    record(
                        "approved_user_enabled",
                        user.get("accountEnabled") is True
                        and user.get("id") == config["approved_user_object_id"],
                    )
                    principals = {}
                    for kind in ("api", "frontend"):
                        sp = read_cli(
                            "az", "ad", "sp", "show", "--id", config[f"{kind}_client_id"], "--output", "json"
                        )
                        principals[kind] = sp
                        record(
                            f"{kind}_sign_in_enabled",
                            sp.get("accountEnabled") is True,
                            "Keep disabled until the private callback and authentication are configured.",
                        )
                        assignments = read_cli(
                            "az",
                            "rest",
                            "--method",
                            "get",
                            "--url",
                            f"https://graph.microsoft.com/v1.0/servicePrincipals/{sp['id']}"
                            "/appRoleAssignedTo",
                            "--output",
                            "json",
                        )
                        record(
                            f"{kind}_sole_owner_assignment",
                            sp.get("appRoleAssignmentRequired") is True
                            and single_owner_assignments(assignments, config["approved_user_object_id"]),
                        )
                    grants = read_cli(
                        "az",
                        "rest",
                        "--method",
                        "get",
                        "--url",
                        "https://graph.microsoft.com/v1.0/oauth2PermissionGrants?$filter=clientId"
                        f" eq '{principals['frontend']['id']}'",
                        "--output",
                        "json",
                    )
                    consent = any(
                        g.get("resourceId") == principals["api"]["id"]
                        and "access_as_user" in g.get("scope", "").split()
                        and (
                            g.get("consentType") == "AllPrincipals"
                            or (
                                g.get("consentType") == "Principal"
                                and g.get("principalId") == config["approved_user_object_id"]
                            )
                        )
                        for g in grants.get("value", [])
                    )
                    record("api_delegated_consent", consent and not grants.get("@odata.nextLink"))
                    environment_id = config.get("existing_environment_resource_id")
                    if environment_id:
                        env = read_cli(
                            "az",
                            "resource",
                            "show",
                            "--ids",
                            environment_id,
                            "--api-version",
                            "2025-07-01",
                            "--output",
                            "json",
                        )
                        properties = env.get("properties", {})
                        record(
                            "reused_environment_private",
                            properties.get("publicNetworkAccess") == "Disabled"
                            and properties.get("vnetConfiguration", {}).get("internal") is True,
                        )
                except (RuntimeError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
                    record(
                        "entra_metadata_complete",
                        False,
                        "Check incomplete; verify tenant login, registrations and read permissions.",
                    )
    except (ValueError, OSError, TypeError):
        record("configuration_readable", False, "Preflight configuration is missing or invalid.")
    passed = bool(checks) and all(c["status"] == "pass" for c in checks)
    report = {
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "automatic_checks_passed": passed,
        "scope": "Read-only metadata; not cloud login/network/SQL acceptance or provisioning approval.",
        "checks": checks,
        "remaining_manual_gates": [
            "Approved private browser route, DNS, subnet restrictions and cost quote",
            "Reviewed template what-if, identity grants and credential-expiry plan",
            "Actual platform sign-in, refresh/logout and Azure SQL acceptance after private provisioning",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
