"""Read-only inventory for the configured Azure model resource; never retrieves keys."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from backend.config import Settings


def main() -> int:
    az = shutil.which("az")
    if not az:
        print("Azure CLI is unavailable.")
        return 1

    def read(*args: str) -> Any:
        result = subprocess.run([az, *args, "--output", "json"], capture_output=True, text=True, timeout=45)
        if result.returncode:
            raise RuntimeError("Read-only Azure inventory failed; verify login and Reader permissions.")
        return json.loads(result.stdout)

    try:
        settings = Settings()
        hostname = urlsplit(settings.azure_openai_endpoint).hostname
        accounts = read("cognitiveservices", "account", "list")
        matches = [a for a in accounts if urlsplit(a["properties"].get("endpoint", "")).hostname == hostname]
        if len(matches) != 1:
            print("Configured endpoint did not uniquely match an account in the current subscription.")
            return 1
        account = matches[0]
        deployment = read(
            "cognitiveservices",
            "account",
            "deployment",
            "show",
            "--name",
            account["name"],
            "--resource-group",
            account["resourceGroup"],
            "--deployment-name",
            settings.azure_openai_deployment,
        )
        properties = deployment["properties"]
        resources = read(
            "resource",
            "list",
            "--resource-group",
            account["resourceGroup"],
            "--query",
            "[].{type:type,location:location}",
        )
        report = {
            "deployment": deployment["name"],
            "location": account["location"],
            "model": properties.get("model"),
            "sku": deployment.get("sku"),
            "provisioning_state": properties.get("provisioningState"),
            "rate_limits": properties.get("rateLimits"),
            "public_network_access": account["properties"].get("publicNetworkAccess"),
            "local_auth_disabled": account["properties"].get("disableLocalAuth", False),
            "resource_types_in_same_group": resources,
        }
        Path("artifacts").mkdir(exist_ok=True)
        Path("artifacts/azure-inventory.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0
    except Exception:
        print(
            "Read-only Azure inventory failed; verify login, endpoint and Reader permissions. "
            "No changes made."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
