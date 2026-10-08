"""Portable, standard-library-only Docker Desktop lifecycle. No implicit inference calls."""

import argparse
import json
import os
import subprocess
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.init_local import main as initialize

ROOT = Path(__file__).resolve().parents[1]


def docker(arguments: list[str]) -> str:
    result = subprocess.run(
        ["docker", *arguments], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode:
        # Compose errors and container logs can include environment values. Never echo them.
        raise RuntimeError(f"Docker operation failed (exit {result.returncode}); raw output suppressed.")
    return result.stdout


def require_local_engine() -> None:
    context = json.loads(docker(["context", "inspect"]))[0]
    endpoints = [context["Endpoints"]["docker"]["Host"]]
    if os.environ.get("DOCKER_HOST"):
        endpoints.append(os.environ["DOCKER_HOST"])
    if any(not endpoint.startswith(("npipe://", "unix://")) for endpoint in endpoints):
        raise RuntimeError("Select the local Docker Desktop context; remote Docker engines are refused.")
    if docker(["info", "--format", "{{.OSType}}"]).strip() != "linux":
        raise RuntimeError("Docker Desktop must be running Linux containers with WSL 2 integration.")


def compose(mode: str = "mock") -> list[str]:
    command = ["compose", "--project-directory", str(ROOT), "--env-file", str(ROOT / ".env")]
    command += ["-f", str(ROOT / "compose.yaml")]
    if mode == "live":
        command += ["-f", str(ROOT / "compose.azure.yaml")]
    return command


def check_configuration(mode: str) -> None:
    config = json.loads(docker([*compose(mode), "--profile", "app", "config", "--format", "json"]))
    for service in config["services"].values():
        for port in service.get("ports", []):
            if port.get("host_ip") != "127.0.0.1":
                raise RuntimeError("Local published ports must bind only to 127.0.0.1.")
    backend = config["services"]["backend"]["environment"]
    frontend = config["services"]["frontend"]["environment"]
    if backend.get("AGENT_MODE") != ("azure" if mode == "live" else "mock"):
        raise RuntimeError("Compose provider mode does not match the requested mode.")
    if backend.get("SQL_HOST") != "sqlserver" or backend.get("APP_ENV", "local") != "local":
        raise RuntimeError("Local launch must use the local synthetic SQL container.")
    if backend.get("SQL_ADMIN_PASSWORD") or any(
        frontend.get(key) for key in ("SQL_PASSWORD", "SQL_ADMIN_PASSWORD", "AZURE_OPENAI_API_KEY")
    ):
        raise RuntimeError("Unexpected privileged credential in an application container.")
    if not backend.get("LOCAL_API_TOKEN") or not backend.get("SQL_PASSWORD"):
        raise RuntimeError("Local authentication and database credentials are required.")


def safe_status() -> list[dict[str, Any]]:
    raw = docker([*compose(), "--profile", "app", "ps", "--all", "--format", "json"]).strip()
    records = json.loads(raw) if raw.startswith("[") else [json.loads(line) for line in raw.splitlines()]
    return [{key: item.get(key) for key in ("Service", "State", "Health", "ExitCode")} for item in records]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "stop", "status", "test", "verify-live"])
    parser.add_argument("--mode", choices=["mock", "live"], default="mock", help="Only applies to start")
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--allow-cloud-call", action="store_true", help="One live verification question only")
    args = parser.parse_args()
    if args.action == "verify-live" and not args.allow_cloud_call:
        parser.error("verify-live requires --allow-cloud-call (one billable inference)")
    if args.allow_cloud_call and args.action != "verify-live":
        parser.error("Only verify-live accepts --allow-cloud-call")
    if args.mode != "mock" and args.action != "start":
        parser.error("--mode applies only to start")
    os.chdir(ROOT)
    try:
        require_local_engine()
        if not (ROOT / ".env").exists():
            if args.action not in {"start", "test"}:
                raise RuntimeError("No local .env exists; run start or test to initialize it.")
            initialize()
        if args.action == "start":
            check_configuration(args.mode)
            print(f"Starting local {args.mode} mode; waiting for SQL, API and UI health.", flush=True)
            docker(
                [
                    *compose(args.mode),
                    "--profile",
                    "app",
                    "up",
                    "-d",
                    "--build",
                    "--wait",
                    "--wait-timeout",
                    "240",
                ]
            )
            if args.mode == "live":
                docker(
                    [
                        *compose(),
                        "exec",
                        "-T",
                        "backend",
                        "python",
                        "-m",
                        "scripts.verify_live",
                        "--check-config",
                        "--docker",
                    ]
                )
            print("Ready: http://127.0.0.1:8501/ - no model query was submitted during launch.")
            if args.open_browser:
                webbrowser.open("http://127.0.0.1:8501/")
        elif args.action == "stop":
            docker([*compose(), "--profile", "app", "--profile", "test", "stop", "--timeout", "30"])
            print("Stopped. SQL volume, .env, evaluation evidence and images are preserved.")
        elif args.action == "test":
            check_configuration("mock")
            (ROOT / "artifacts").mkdir(exist_ok=True)
            print(
                "Running SQL regression, recorded replay, Learning Mode and security tests; no inference.",
                flush=True,
            )
            output = docker([*compose(), "--profile", "test", "run", "--build", "--rm", "tests"])
            # Only emit the pytest summary, not pip/container logs or raw test diagnostics.
            for line in output.splitlines():
                if " passed" in line and " in " in line:
                    print(line)
            print("Passed. Evidence: artifacts/tests.xml and artifacts/evaluation.json")
        elif args.action == "verify-live":
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            target = ROOT / "artifacts" / f"portable-live-{stamp}.json"
            target.parent.mkdir(exist_ok=True)
            remote = f"/tmp/portable-live-{stamp}.json"
            print("Submitting one authorized live question through the local API.", flush=True)
            docker(
                [
                    *compose(),
                    "exec",
                    "-T",
                    "backend",
                    "python",
                    "-m",
                    "scripts.verify_live",
                    "--allow-cloud-call",
                    "--api-url",
                    "http://127.0.0.1:8000",
                    "--output",
                    remote,
                ]
            )
            # Docker's archive/cp path cannot read this read-only container's tmpfs consistently.
            # Read only the named synthetic report through exec; never export environment/logs.
            report = docker(
                [
                    *compose(),
                    "exec",
                    "-T",
                    "backend",
                    "python",
                    "-c",
                    "from pathlib import Path; import sys; print(Path(sys.argv[1]).read_text())",
                    remote,
                ]
            )
            json.loads(report)
            with target.open("x", encoding="utf-8") as report_file:
                report_file.write(report)
            print(f"Independent live result verification passed. Evidence: artifacts/{target.name}")
        else:
            print(json.dumps(safe_status(), indent=2))
        return 0
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(
            str(exc)
            if isinstance(exc, RuntimeError)
            else "Local operation failed; check Docker Desktop and configuration."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
