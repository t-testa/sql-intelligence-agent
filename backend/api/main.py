import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.agent.conversation import ConversationError
from backend.agent.examples import EXAMPLES
from backend.agent.provider import (
    AzureResponsesProvider,
    MockProvider,
    ModelError,
    ProposalProvider,
)
from backend.agent.service import AgentService
from backend.config import Settings
from backend.contracts import Answer, PracticeRequest, QuestionRequest, SQLRequest
from backend.database.connection import make_engine
from backend.database.executor import (
    BusyError,
    ExecutionError,
    QueryBackend,
    QueryTimeoutError,
    ResultLimitError,
    SQLServerBackend,
)
from backend.security.auth import Authenticator, Principal
from backend.security.gateway import PolicyError
from backend.semantic.catalog import GRAINS, METRICS

logger = logging.getLogger("sia.audit")


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        body = bytearray()
        while True:
            try:
                message = await asyncio.wait_for(receive(), timeout=10)
            except asyncio.TimeoutError:
                await JSONResponse({"detail": "Request body timeout"}, 408)(scope, receive, send)
                return
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > 65536:
                await JSONResponse({"detail": "Request too large"}, 413)(scope, receive, send)
                return
            if not message.get("more_body", False):
                break
        consumed = False

        async def bounded_receive() -> Message:
            nonlocal consumed
            if consumed:
                return await receive()
            consumed = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, bounded_receive, send)


def create_app(
    settings: Settings | None = None,
    provider: ProposalProvider | None = None,
    backend: QueryBackend | None = None,
) -> FastAPI:
    config = settings or Settings()
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)
    logger.propagate = False
    authenticator = Authenticator(config)
    db = backend or SQLServerBackend(make_engine(config), config)
    model = provider or (MockProvider() if config.agent_mode == "mock" else AzureResponsesProvider(config))
    service = AgentService(model, db, config.max_concurrent_queries)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if isinstance(db, SQLServerBackend):
            db.verify_identity()
        yield
        if isinstance(db, SQLServerBackend):
            db.engine.dispose()

    app = FastAPI(
        title="SQL Intelligence Agent",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if config.app_env == "local" else None,
        redoc_url=None,
    )
    app.add_middleware(BodyLimitMiddleware)

    @app.exception_handler(PolicyError)
    async def policy_error(request: Request, exc: PolicyError) -> JSONResponse:
        logger.info(json.dumps({"event": "policy_rejected", "path": request.url.path}))
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.exception_handler(ExecutionError)
    async def execution_error(request: Request, exc: ExecutionError) -> JSONResponse:
        status = (
            429
            if isinstance(exc, BusyError)
            else (
                504
                if isinstance(exc, QueryTimeoutError)
                else 413
                if isinstance(exc, ResultLimitError)
                else 503
            )
        )
        logger.info(json.dumps({"event": "execution_rejected", "status": status}))
        return JSONResponse({"detail": str(exc)}, status_code=status)

    @app.exception_handler(ModelError)
    async def model_error(request: Request, exc: ModelError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=502)

    @app.exception_handler(ConversationError)
    async def conversation_error(request: Request, exc: ConversationError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/catalog")
    def catalog(principal: Annotated[Principal, Depends(authenticator.authenticate)]) -> dict[str, Any]:
        return {
            "mode": config.agent_mode,
            "model_deployment": config.azure_openai_deployment if config.agent_mode == "azure" else None,
            "conversation": {"max_turns": 12, "idle_timeout_seconds": 1800},
            "backend": db.name,
            "grains": GRAINS,
            "metrics": METRICS,
            "examples": [{"id": e.id, "question": e.question} for e in EXAMPLES],
            "limits": {
                "rows": config.max_result_rows,
                "bytes": config.max_result_bytes,
                "timeout_seconds": config.query_timeout_seconds,
            },
        }

    @app.post("/questions", response_model=Answer)
    def ask(
        body: QuestionRequest, principal: Annotated[Principal, Depends(authenticator.authenticate)]
    ) -> Answer:
        return service.ask(body.question, principal.subject, body.conversation_id)

    @app.delete("/conversations/{conversation_id}")
    def clear_conversation(
        conversation_id: UUID, principal: Annotated[Principal, Depends(authenticator.authenticate)]
    ) -> dict[str, bool]:
        service.conversations.clear(str(conversation_id), principal.subject)
        return {"cleared": True}

    @app.post("/sql/validate")
    def validate(
        body: SQLRequest, principal: Annotated[Principal, Depends(authenticator.authenticate)]
    ) -> dict[str, Any]:
        query = service.gateway.validate(body.sql, body.parameters)
        return {"valid": True, "sql": query.display_sql, "views": query.views}

    @app.post("/practice")
    def practice(
        body: PracticeRequest, principal: Annotated[Principal, Depends(authenticator.authenticate)]
    ) -> dict[str, Any]:
        try:
            return service.practice(body.exercise_id, body.sql, body.parameters)
        except PolicyError:
            raise
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    return app


# Factory keeps importing this module safe for offline tests and tooling.
# Start with: uvicorn backend.api.main:create_app --factory
