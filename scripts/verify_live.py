"""Offline configuration check, or one explicitly authorized live question through the API."""

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import sqlglot
from pydantic import ValidationError
from sqlglot import exp

from backend.config import Settings
from backend.contracts import ResultTable, Scalar
from backend.database.connection import make_engine
from backend.database.executor import SQLServerBackend
from backend.security.gateway import SQLGateway

FIRST_QUESTION = (
    "For every job, show the invoice with the highest amount. Include JobID, InvoiceID, and Amount. "
    "Use ROW_NUMBER() to handle the ranking. Include jobs with no invoices with NULL InvoiceID and Amount. "
    "Break equal amounts by the lowest InvoiceID. Order by JobID."
)


def invoice_winners(jobs: ResultTable, invoices: ResultTable) -> list[list[Scalar]]:
    """Independent Python oracle: no window SQL, model or catalog examples involved."""
    winners: dict[int, tuple[int, Decimal]] = {}
    for invoice_id, job_id, amount in invoices.rows:
        key, invoice = int(str(job_id)), int(str(invoice_id))
        value = Decimal(str(amount))
        previous = winners.get(key)
        if previous is None or value > previous[1] or (value == previous[1] and invoice < previous[0]):
            winners[key] = (invoice, value)
    rows: list[list[Scalar]] = []
    for job in jobs.rows:
        job_id = int(str(job[0]))
        best = winners.get(job_id)
        rows.append([job_id, best[0] if best else None, str(best[1]) if best else None])
    return sorted(rows, key=lambda row: int(str(row[0])))


def verify_answer(answer: dict[str, Any], expected: list[list[Scalar]]) -> None:
    if answer.get("status") != "answered" or not answer.get("sql"):
        raise ValueError(
            "The model asked for clarification instead of answering the explicit smoke question."
        )
    if not sqlglot.parse_one(answer["sql"], read="tsql").find(exp.RowNumber):
        raise ValueError("The generated SQL did not use the requested ROW_NUMBER().")
    result = answer["result"]
    if [column.lower() for column in result["columns"]] != ["jobid", "invoiceid", "amount"]:
        raise ValueError("Expected JobID, InvoiceID and Amount in that order.")
    actual = result["rows"]
    if len(actual) != len(expected) or result["truncated"]:
        raise ValueError("The live query did not return exactly one row per job.")
    for row, reference in zip(actual, expected, strict=True):
        if row[:2] != reference[:2] or (
            row[2] != reference[2]
            and (row[2] is None or reference[2] is None or Decimal(str(row[2])) != Decimal(str(reference[2])))
        ):
            raise ValueError("The live result differs from the independent invoice maximum/tie oracle.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-config", action="store_true", help="Offline only (also the default)")
    parser.add_argument("--docker", action="store_true", help="Require a key for the local Docker override")
    parser.add_argument("--allow-cloud-call", action="store_true", help="Authorize one billable question")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=Path("artifacts/first-live-query.json"))
    args = parser.parse_args()
    if args.check_config and args.allow_cloud_call:
        parser.error("Choose --check-config or --allow-cloud-call, not both")
    try:
        settings = Settings(agent_mode="azure")
    except ValidationError:
        print(
            "Configuration incomplete: set a valid HTTPS AZURE_OPENAI_ENDPOINT and deployment; "
            "check numeric limits and authentication settings. No network request was made."
        )
        return 2
    key_present = bool(settings.azure_openai_api_key.get_secret_value())
    if args.docker and not key_present:
        print("The Docker override requires AZURE_OPENAI_API_KEY. Use host Python for Azure CLI identity.")
        return 2
    print(
        json.dumps(
            {
                "configuration": "valid",
                "deployment": settings.azure_openai_deployment,
                "authentication": "resource API key" if key_present else "Azure identity (not yet verified)",
                "provider_retries": 0,
                "max_output_tokens": settings.azure_openai_max_output_tokens,
                "note": "Azure connectivity, credentials, quota and model availability remain unverified.",
            },
            indent=2,
        )
    )
    if not args.allow_cloud_call:
        return 0
    if settings.app_env != "local" or settings.auth_mode != "local":
        print(
            "This smoke helper supports the local application only; use delegated Entra for cloud API checks."
        )
        return 2
    engine = make_engine(settings)
    try:
        with httpx.Client(
            base_url=args.api_url,
            headers={"Authorization": f"Bearer {settings.local_api_token.get_secret_value()}"},
            timeout=65,
        ) as client:
            catalog_response = client.get("/catalog")
            catalog_response.raise_for_status()
            catalog = catalog_response.json()
            if catalog["mode"] != "azure" or catalog["model_deployment"] != settings.azure_openai_deployment:
                raise ValueError(
                    "The running API is not using the configured Azure deployment. Restart it in live mode."
                )
            backend = SQLServerBackend(engine, settings)
            backend.verify_identity()
            gateway = SQLGateway()
            jobs = backend.execute(gateway.validate("SELECT JobId FROM reporting.vJobs"))
            invoices = backend.execute(
                gateway.validate("SELECT InvoiceId, JobId, Amount FROM reporting.vInvoices")
            )
            expected = invoice_winners(jobs, invoices)
            print("Submitting one explicitly authorized live question. No automatic retries.")
            response = client.post("/questions", json={"question": FIRST_QUESTION})
            if response.is_error:
                # Only the application controls this detail; Azure response bodies are never forwarded.
                detail = response.json().get("detail", "Check application configuration.")
                raise ValueError(f"The API rejected the question (HTTP {response.status_code}): {detail}")
            answer = response.json()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(answer, indent=2), encoding="utf-8")
            verify_answer(answer, expected)
            print(answer["sql"])
            print(
                f"PASS: {len(expected)} job rows match the independent Python oracle. Evidence: {args.output}"
            )
            return 0
    except Exception as exc:
        # Known ValueErrors contain only our fixed guidance. Other errors may contain connection secrets.
        print(
            str(exc)
            if type(exc) is ValueError
            else "Verification failed; check API and SQL connectivity/configuration."
        )
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
