"""Pure deterministic source records. No database/network dependency or model calls."""

from datetime import date
from decimal import Decimal
from typing import Any

REGIONS = ("Central", "East", "North", "West")


def dataset() -> dict[str, list[dict[str, Any]]]:
    data: dict[str, list[dict[str, Any]]] = {
        name: [] for name in ("Customers", "Jobs", "Invoices", "Expenses", "Targets")
    }
    for i in range(1, 61):
        data["Customers"].append(
            {
                "CustomerId": i,
                "CustomerName": f"Synthetic Customer {i:03d}",
                "Region": REGIONS[(i - 1) % 4],
                "Segment": ("Commercial", "Industrial", "Public")[(i - 1) % 3],
                "InternalNote": "Synthetic internal field; deliberately not exposed to the agent",
            }
        )
    for i in range(1, 241):
        month = (i - 1) // 20 + 1
        value = Decimal(10000 + ((i * 173) % 90000))
        status = "Planned" if i % 12 == 0 else "Active" if i % 5 == 0 else "Completed"
        data["Jobs"].append(
            {
                "JobId": i,
                "CustomerId": (i - 1) % 60 + 1,
                "StartDate": date(2025, month, (i - 1) % 20 + 1),
                "Status": status,
                "ContractValue": value,
                "BudgetAmount": value * Decimal("0.70"),
            }
        )
        for part, ratio in enumerate((Decimal("0.4"), Decimal("0.6")), start=1):
            factor = (
                Decimal(0) if status == "Planned" else (Decimal("0.6") if status == "Active" else Decimal(1))
            )
            data["Invoices"].append(
                {
                    "InvoiceId": (i - 1) * 2 + part,
                    "JobId": i,
                    "InvoiceDate": date(2025, month, 22 + part),
                    "Amount": (value * ratio * factor).quantize(Decimal("0.01")),
                }
            )
        for part, category in enumerate(("Labor", "Materials", "Travel"), start=1):
            ratio = (Decimal("0.30"), Decimal("0.25"), Decimal("0.08"))[part - 1]
            if i % 7 == 0:
                ratio += Decimal("0.08")
            factor = Decimal("0.05") if status == "Planned" else Decimal(1)
            data["Expenses"].append(
                {
                    "ExpenseId": (i - 1) * 3 + part,
                    "JobId": i,
                    "ExpenseDate": date(2025, month, 21 + part),
                    "Category": category,
                    "Amount": (value * ratio * factor).quantize(Decimal("0.01")),
                }
            )
    for month in range(1, 13):
        for index, region in enumerate(REGIONS):
            data["Targets"].append(
                {
                    "TargetId": (month - 1) * 4 + index + 1,
                    "PeriodStart": date(2025, month, 1),
                    "Region": region,
                    "RevenueTarget": Decimal(100000 + month * 5000 + index * 2000),
                    "MarginTargetPct": Decimal("30.00"),
                }
            )
    return data
