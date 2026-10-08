"""Read public Azure retail prices; no Azure account authentication or resource mutation."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


def main() -> None:
    filters = {
        "sql_basic": (
            "productName eq 'SQL Database Single Basic' and armRegionName eq 'canadaeast' and skuName eq 'B'"
        ),
        "container_apps": "serviceName eq 'Azure Container Apps' and armRegionName eq 'canadaeast'",
        "openai": (
            "contains(productName, 'OpenAI') and contains(meterName, '4.1') and armRegionName eq 'canadaeast'"
        ),
        "private_link": "contains(productName, 'Private Link') and armRegionName eq 'canadaeast'",
        "registry": (
            "serviceName eq 'Container Registry' and armRegionName eq 'canadaeast' and skuName eq 'Basic'"
        ),
    }
    output: dict[str, Any] = {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "currency": "USD",
        "items": {},
    }
    with httpx.Client(timeout=30) as client:
        for name, expression in filters.items():
            response = client.get(
                "https://prices.azure.com/api/retail/prices", params={"$filter": expression}
            )
            response.raise_for_status()
            body = response.json()
            rows = body["Items"]
            # Preserve only related meters, not a broad account/resource inventory.
            if name == "openai":
                rows = [
                    row
                    for row in rows
                    if row["skuName"]
                    in {"gpt 4.1 mini Inp glbl", "gpt 4.1 mini Outp glbl", "gpt 4.1 mini cached Inp glbl"}
                ]
            output["items"][name] = [
                {
                    key: row.get(key)
                    for key in (
                        "productName",
                        "skuName",
                        "meterName",
                        "retailPrice",
                        "unitOfMeasure",
                        "type",
                        "effectiveStartDate",
                    )
                }
                for row in rows
            ]
            output[name + "_has_more"] = bool(body.get("NextPageLink"))
    Path("artifacts/pricing-snapshot.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
