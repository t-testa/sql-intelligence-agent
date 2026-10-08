"""Bounded, owner-scoped conversation memory for the single-process application.

Only questions and accepted proposals are retained. Database results never enter model context.
Limits fail explicitly instead of silently discarding context. Restarting the API clears memory.
"""

import threading
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from backend.contracts import Proposal
from backend.database.executor import BusyError


class ConversationError(ValueError):
    pass


@dataclass(frozen=True)
class ConversationTurn:
    question: str
    proposal_json: str

    @classmethod
    def accepted(cls, question: str, proposal: Proposal) -> "ConversationTurn":
        return cls(question, proposal.model_dump_json())


@dataclass
class Conversation:
    id: str
    subject: str
    touched: float
    turns: list[ConversationTurn] = field(default_factory=list)
    active: bool = False


class ConversationStore:
    def __init__(
        self, ttl_seconds: int = 1800, capacity: int = 128, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.ttl = ttl_seconds
        self.capacity = capacity
        self.clock = clock
        self._lock = threading.Lock()
        self._sessions: dict[str, Conversation] = {}

    @contextmanager
    def lease(self, conversation_id: str | None, subject: str) -> Iterator[Conversation]:
        with self._lock:
            now = self.clock()
            self._sessions = {
                key: value
                for key, value in self._sessions.items()
                if value.active or now - value.touched < self.ttl
            }
            if conversation_id is None:
                if len(self._sessions) >= self.capacity:
                    raise BusyError("Conversation capacity is busy; clear a conversation or retry later")
                session = Conversation(str(uuid.uuid4()), subject, now)
                self._sessions[session.id] = session
            else:
                existing = self._sessions.get(conversation_id)
                if existing is None or existing.subject != subject:
                    raise ConversationError("Conversation unavailable or expired. Start a new conversation.")
                session = existing
            if session.active:
                raise BusyError("A request is already running in this conversation")
            if (
                len(session.turns) >= 12
                or sum(len(turn.question) + len(turn.proposal_json) for turn in session.turns) >= 32000
            ):
                raise ConversationError("Conversation context limit reached. Start a new conversation.")
            session.active = True
        try:
            yield session
        finally:
            with self._lock:
                session.active = False
                session.touched = self.clock()
                if not session.turns:
                    self._sessions.pop(session.id, None)

    def clear(self, conversation_id: str, subject: str) -> None:
        with self._lock:
            session = self._sessions.get(conversation_id)
            if session is None or session.subject != subject:
                raise ConversationError("Conversation unavailable or expired. Start a new conversation.")
            if session.active:
                raise BusyError("A request is already running in this conversation")
            del self._sessions[conversation_id]
