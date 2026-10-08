"""Single-process rolling budgets. Attempts count even if inference/validation fails."""

import threading
import time
from collections import deque
from collections.abc import Callable

from backend.database.executor import BusyError


class InferenceBudget:
    def __init__(
        self,
        requests_per_minute: int,
        tokens_per_minute: int,
        daily_requests: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self.daily_requests = daily_requests
        self.clock = clock
        self._minute: deque[tuple[float, int]] = deque()
        self._day: deque[float] = deque()
        self._lock = threading.Lock()

    def consume(self, estimated_tokens: int) -> None:
        with self._lock:
            now = self.clock()
            while self._minute and now - self._minute[0][0] >= 60:
                self._minute.popleft()
            while self._day and now - self._day[0] >= 86400:
                self._day.popleft()
            if estimated_tokens > self.tokens_per_minute:
                raise BusyError("Conversation exceeds the inference budget; start a shorter conversation")
            if len(self._day) >= self.daily_requests:
                raise BusyError("Daily inference request budget reached")
            if (
                len(self._minute) >= self.requests_per_minute
                or sum(tokens for _, tokens in self._minute) + estimated_tokens > self.tokens_per_minute
            ):
                raise BusyError("Inference rate budget reached; wait one minute before retrying")
            self._minute.append((now, estimated_tokens))
            self._day.append(now)
