"""Independent reference/live/replay evaluation. No model grading, no automatic cloud retries."""

import argparse
import hashlib
import json
import logging
import time
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import sqlglot

from backend.agent.learning import explain, grounded_answer
from backend.agent.provider import SYSTEM_PROMPT, AzureResponsesProvider, ModelError
from backend.config import Settings
from backend.contracts import Proposal, ResultTable
from backend.database.connection import make_engine
from backend.database.executor import ExecutionError, SQLServerBackend, scalar
from backend.security.gateway import PolicyError, SQLGateway
from backend.semantic.catalog import schema_context
from scripts.bootstrap_db import admin_connection

CASES_PATH = Path("evaluation/cases.json")


def normalized_cell(value: Any) -> tuple[str, Any]:
    if value is None:
        return ("null", None)
    if isinstance(value, bool):
        return ("bool", value)
    try:
        number = Decimal(str(value))
        if number.is_finite():
            return ("number", number)
    except InvalidOperation:
        pass
    return ("text", str(value))


def compare(case: dict[str, Any], result: ResultTable) -> list[str]:
    failures = []
    if [c.lower() for c in result.columns] != [c.lower() for c in case["columns"]]:
        failures.append("column_contract")
    actual = [tuple(normalized_cell(v) for v in row) for row in result.rows]
    expected = [tuple(normalized_cell(v) for v in row) for row in case["rows"]]
    if result.truncated or result.row_count != len(expected) or len(actual) != len(expected):
        failures.append("completeness")
    if Counter(actual) != Counter(expected):
        failures.append("values_precision_nulls_or_duplicates")
    elif case["ordered"] and actual != expected:
        failures.append("ordering")
    return failures


def check_narrative(result: ResultTable, answer: str) -> bool:
    """Independent checks against deterministic answer grammar, never an LLM judge."""
    if not result.rows:
        return answer == "The query returned no matching rows. Review the filters before drawing conclusions."
    if len(result.rows) > 1:
        return answer == (
            f"The query returned {len(result.rows)} rows with {', '.join(result.columns)}. "
            "The complete bounded result is shown below; financial amounts use CAD."
        )
    expected_facts = [
        f"{name}: {'not defined' if value is None else value}"
        for name, value in zip(result.columns, result.rows[0], strict=True)
    ]
    return answer == "Verified query result — " + "; ".join(expected_facts) + ". Financial amounts use CAD."


class CaptureResponses:
    def __init__(self, responses: Any) -> None:
        self.responses = responses
        self.receipt: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> Any:
        response = self.responses.create(**kwargs)
        self.receipt = {
            "deployment_requested": kwargs["model"],
            "response_id": response.id,
            "request_id": getattr(response, "_request_id", None),
            "model_returned": response.model,
            "status": response.status,
            "usage": response.usage.model_dump() if response.usage else None,
            "tool_calls": [
                {"name": item.name, "arguments": item.arguments}
                for item in response.output
                if item.type == "function_call"
            ],
        }
        return response


def assess(case: dict[str, Any], proposal: Proposal, db: SQLServerBackend) -> dict[str, Any]:
    outcome: dict[str, Any] = {"proposal": proposal.model_dump(), "failures": []}
    if proposal.action == "clarify":
        outcome["failures"] = [] if case["expect"] == "clarify" else ["unexpected_clarification"]
        outcome["explanation"] = proposal.clarification
        return outcome
    if case["expect"] == "clarify":
        # Validation still runs for forbidden proposals; execution is never needed for deny cases.
        try:
            SQLGateway().validate(proposal.sql, proposal.parameters)
            outcome["failures"] = ["failed_to_clarify_or_refuse"]
        except PolicyError:
            outcome["failures"] = ["unsafe_proposal_blocked"]
        return outcome
    try:
        query = SQLGateway().validate(proposal.sql, proposal.parameters)
        result = db.execute(query)
        outcome["validated_sql"] = query.display_sql
        outcome["result"] = result.model_dump()
        outcome["failures"] = compare(case, result)
        tree = sqlglot.parse_one(query.display_sql, read="tsql")
        nodes = {type(node).__name__ for node in tree.walk()}
        if not set(case["required_nodes"]).issubset(nodes):
            outcome["failures"].append("requested_sql_construct_missing")
        answer = grounded_answer(result)
        outcome["explanation"] = answer
        outcome["learning"] = explain(query).model_dump()
        if not check_narrative(result, answer):
            outcome["failures"].append("unsupported_narrative")
    except PolicyError as exc:
        outcome["failures"] = ["policy_rejection"]
        outcome["detail"] = str(exc)
    except ExecutionError as exc:
        outcome["failures"] = ["execution_failure"]
        outcome["detail"] = str(exc)
    return outcome


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["references", "live", "replay"], default="references")
    parser.add_argument("--allow-cloud-call", action="store_true")
    parser.add_argument("--azure-sql", action="store_true", help="Approved private Azure SQL acceptance only")
    parser.add_argument(
        "--env-file", type=Path, default=Path(".env"), help="Separate private configuration file"
    )
    parser.add_argument("--ids", help="Comma-separated case IDs; omitted means the entire frozen suite")
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=12.0,
        help="Minimum spacing of live requests, no automatic retries",
    )
    parser.add_argument("--recording", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "live" and not args.allow_cloud_call:
        parser.error("Live inference requires --allow-cloud-call")
    if args.output.exists():
        parser.error("Output already exists; choose a new path to preserve previous evidence")
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if args.ids:
        requested = set(args.ids.split(","))
        if requested - {case["id"] for case in cases}:
            parser.error("Unknown case ID")
        cases = [case for case in cases if case["id"] in requested]
    if len(cases) > args.limit or not 1 <= args.limit <= 100:
        parser.error("Set an explicit limit between suite size and 100 calls")
    for logger_name in ("httpx", "httpcore", "openai", "azure"):
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)
    settings = Settings(_env_file=args.env_file)  # type: ignore[call-arg]
    if args.azure_sql:
        from scripts.azure_sql import validate_target

        validate_target(settings.sql_host, "SQLIntelligence", settings.entra_tenant_id)
        if settings.app_env != "cloud" or not settings.sql_managed_identity:
            parser.error("Azure SQL acceptance requires cloud settings and runtime managed identity")
    elif settings.sql_host not in {"127.0.0.1", "localhost", "sqlserver"} or settings.app_env != "local":
        parser.error("This evaluation is restricted to the existing local synthetic SQL Server")
    if args.mode == "live" and settings.azure_openai_deployment != "sql-agent-model":
        parser.error("This authorized run must target sql-agent-model")
    records = {}
    if args.mode == "replay":
        if not args.recording:
            parser.error("Replay requires --recording")
        recorded = json.loads(args.recording.read_text(encoding="utf-8"))
        records = {record["id"]: record for record in recorded["outcomes"]}
    report: dict[str, Any] = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "database_target": "azure_sql" if args.azure_sql else "local_sql_server",
        "deployment": settings.azure_openai_deployment if args.mode == "live" else None,
        "max_output_tokens": settings.azure_openai_max_output_tokens,
        "interval_seconds": args.interval_seconds if args.mode == "live" else None,
        "contract_sha256": hashlib.sha256(
            json.dumps(Proposal.model_json_schema(), sort_keys=True).encode()
        ).hexdigest(),
        "suite_sha256": hashlib.sha256(CASES_PATH.read_bytes()).hexdigest(),
        "prompt_sha256": hashlib.sha256((SYSTEM_PROMPT + "\n" + schema_context()).encode()).hexdigest(),
        "outcomes": [],
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "security_grade": "separate mandatory pytest gate",
        "release_validated": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save() -> None:
        report["total"] = len(report["outcomes"])
        report["passed"] = sum(not item["failures"] for item in report["outcomes"])
        report["failed"] = report["total"] - report["passed"]
        report["failure_classes"] = dict(Counter(f for item in report["outcomes"] for f in item["failures"]))
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    backends = {}
    model = None
    capture = None
    try:
        for fixture, database in [("baseline", "SQLIntelligence"), ("edge", "SQLIntelligenceValidation")]:
            config = settings.model_copy(update={"sql_database": database})
            db = SQLServerBackend(make_engine(config), config)
            # Cloud reference SQL runs as the separate CLI-authenticated migration operator.
            # Model/replay execution still verifies and uses only the runtime managed identity.
            if not (args.azure_sql and args.mode == "references"):
                db.verify_identity()
            backends[fixture] = db
        if args.mode == "live":
            model = AzureResponsesProvider(settings)
            capture = CaptureResponses(model.client.responses)
            model.client.responses = capture
        for case in cases:
            started = time.monotonic()
            outcome: dict[str, Any] = {
                "id": case["id"],
                "category": case["category"],
                "fixture": case["fixture"],
                "question": case["question"],
                "failures": [],
            }
            try:
                if args.mode == "references":
                    if case["expect"] == "query":
                        database = backends[case["fixture"]].settings.sql_database
                        if args.azure_sql:
                            from scripts.azure_sql import admin_connection as cloud_admin_connection

                            connection = cloud_admin_connection(
                                settings.sql_host, database, settings.entra_tenant_id
                            )
                        else:
                            connection = admin_connection(database)
                        try:
                            cursor = connection.execute(case["reference_sql"])
                            columns = [column[0] for column in cursor.description]
                            rows = [[scalar(value) for value in row] for row in cursor.fetchall()]
                            result = ResultTable(
                                columns=columns, rows=rows, row_count=len(rows), elapsed_ms=0
                            )
                        finally:
                            connection.close()
                        outcome["failures"] = compare(case, result)
                        outcome["result"] = result.model_dump()
                else:
                    if args.mode == "live":
                        assert model is not None and capture is not None
                        capture.receipt = {}
                        proposal = model.propose(case["question"])
                        outcome["receipt"] = capture.receipt
                        usage = capture.receipt.get("usage") or {}
                        report["total_input_tokens"] += usage.get("input_tokens", 0)
                        report["total_output_tokens"] += usage.get("output_tokens", 0)
                    else:
                        proposal = Proposal.model_validate(records[case["id"]]["proposal"])
                    outcome.update(assess(case, proposal, backends[case["fixture"]]))
            except ModelError as exc:
                outcome["failures"] = ["rate_limited" if "(429)" in str(exc) else "provider_failure"]
                outcome["detail"] = str(exc)
                if capture:
                    outcome["receipt"] = capture.receipt
                    usage = capture.receipt.get("usage") or {}
                    report["total_input_tokens"] += usage.get("input_tokens", 0)
                    report["total_output_tokens"] += usage.get("output_tokens", 0)
            except Exception as exc:
                outcome["failures"] = ["evaluation_error"]
                outcome["error_type"] = type(exc).__name__
            outcome["elapsed_seconds"] = round(time.monotonic() - started, 3)
            report["outcomes"].append(outcome)
            save()
            print(
                f"{case['id']}: {'PASS' if not outcome['failures'] else ', '.join(outcome['failures'])}",
                flush=True,
            )
            if report["total_input_tokens"] > 400000 or report["total_output_tokens"] > 80000:
                report["stopped"] = "Explicit token budget reached"
                break
            if "rate_limited" in outcome["failures"]:
                report["stopped"] = (
                    "Azure rate limit: stop rather than send more requests; rerun remaining IDs later"
                )
                break
            if args.mode == "live":
                time.sleep(max(0, min(args.interval_seconds, 60) - (time.monotonic() - started)))
        report["complete"] = len(report["outcomes"]) == len(cases)
        report["completed_utc"] = datetime.now(timezone.utc).isoformat()
        save()
        print(json.dumps({k: v for k, v in report.items() if k != "outcomes"}, indent=2))
        return 0 if report["complete"] and report["failed"] == 0 else 1
    finally:
        for db in backends.values():
            db.engine.dispose()
        if model:
            model.client.close()


if __name__ == "__main__":
    raise SystemExit(main())
