import hashlib
import json
import logging
import threading
import uuid
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from backend.agent.conversation import ConversationStore, ConversationTurn
from backend.agent.examples import BY_ID, EXAMPLES
from backend.agent.learning import explain, grounded_answer
from backend.agent.provider import ProposalProvider, normalized
from backend.contracts import Answer, Parameter, Proposal, ResultTable
from backend.database.executor import BusyError, QueryBackend
from backend.security.gateway import SQLGateway

logger = logging.getLogger("sia.audit")


def canonical_rows(result: ResultTable) -> Counter[tuple[str, ...]]:
    """Compare unordered multisets, preserving duplicate rows and exact cent precision."""

    def normalize(value: Any) -> str:
        if value is None:
            return "null:"
        try:
            decimal = Decimal(str(value))
            if decimal.is_finite():
                return "number:" + str(decimal.quantize(Decimal("0.01")))
        except InvalidOperation:
            pass
        return "text:" + str(value)

    return Counter(tuple(normalize(value) for value in row) for row in result.rows)


class AgentService:
    def __init__(self, provider: ProposalProvider, backend: QueryBackend, concurrency: int = 3) -> None:
        self.provider = provider
        self.backend = backend
        self.gateway = SQLGateway()
        self.conversations = ConversationStore()
        self._requests = threading.BoundedSemaphore(concurrency)

    def ask(self, question: str, subject: str, conversation_id: str | None = None) -> Answer:
        with self.conversations.lease(conversation_id, subject) as session:
            answer, proposal = self._answer(question, subject, tuple(session.turns))
            if answer.sql:
                proposal = proposal.model_copy(update={"sql": answer.sql})
            session.turns.append(ConversationTurn.accepted(question, proposal))
            return answer.model_copy(update={"conversation_id": session.id})

    def _answer(
        self, question: str, subject: str, history: tuple[ConversationTurn, ...]
    ) -> tuple[Answer, Proposal]:
        if not self._requests.acquire(blocking=False):
            raise BusyError("Request capacity is busy; retry shortly")
        request_id = str(uuid.uuid4())
        try:
            proposal = self.provider.propose(question, history=history)
            if proposal.action == "clarify":
                return Answer(
                    request_id=request_id, status="clarification", answer=proposal.clarification
                ), proposal
            exercise = next((e.id for e in EXAMPLES if normalized(e.question) == normalized(question)), None)
            query = self.gateway.validate(proposal.sql, proposal.parameters)
            result = self.backend.execute(query)
            logger.info(
                json.dumps(
                    {
                        "event": "query_completed",
                        "request_id": request_id,
                        "subject_hash": hashlib.sha256(subject.encode()).hexdigest()[:16],
                        "sql_hash": hashlib.sha256(query.display_sql.encode()).hexdigest(),
                        "rows": result.row_count,
                        "elapsed_ms": result.elapsed_ms,
                    }
                )
            )
            return Answer(
                request_id=request_id,
                status="answered",
                answer=grounded_answer(result),
                sql=query.display_sql,
                parameters=proposal.parameters,
                result=result,
                learning=explain(query, exercise),
            ), proposal
        finally:
            self._requests.release()

    def practice(self, exercise_id: str, sql: str, parameters: list[Parameter]) -> dict[str, Any]:
        if exercise_id not in BY_ID:
            raise ValueError("Unknown practice exercise")
        candidate_query = self.gateway.validate(sql, parameters)
        # Fixtures and reference SQL live outside the proposal provider and are independently verified.
        fixture_path = Path(__file__).resolve().parents[2] / "sql" / "seeds" / "expected_results.json"
        fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))
        fixture = fixtures[exercise_id]
        reference = self.backend.execute(self.gateway.validate(fixture["reference_sql"]))
        expected = ResultTable(
            columns=fixture["columns"],
            rows=fixture["rows"],
            row_count=len(fixture["rows"]),
            elapsed_ms=0,
        )
        if canonical_rows(reference) != canonical_rows(expected):
            raise ValueError("Dataset differs from the independently verified practice fixture")
        candidate = self.backend.execute(candidate_query)
        matches = len(candidate.columns) == len(expected.columns) and (
            canonical_rows(candidate) == canonical_rows(expected)
        )
        return {
            "matches": matches,
            "candidate": candidate.model_dump(),
            "reference": reference.model_dump(),
            "reference_sql": fixture["reference_sql"],
            "feedback": "Matches the independently verified result on this synthetic dataset."
            if matches
            else "Results differ. Check grouping, duplicate rows, filters and metric grain.",
            "comparison": "Unordered row multiset; column positions matter; numbers compared to cents. "
            "Matching one fixture is not a proof of general query equivalence.",
        }
