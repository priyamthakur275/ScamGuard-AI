"""Caps on LLM answers so one visitor (or a burst of traffic) cannot use up the
free Gemini quota. When a cap is reached the Copilot falls back to its
built-in answers instead of failing."""

from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime, timezone

PER_VISITOR = 10           # AI answers per visitor ...
PER_VISITOR_WINDOW = 600   # ... per 10 minutes
_lock = threading.Lock()
_visitors: dict[str, deque[float]] = {}
_day = {"date": "", "count": 0}


def allow(visitor: str, daily_limit: int, now: float | None = None) -> bool:
    """Record one AI answer for `visitor` and return True, or return False
    (recording nothing) when the visitor or the whole service is over its cap."""
    now = time.time() if now is None else now
    today = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
    with _lock:
        if _day["date"] != today:
            _day.update(date=today, count=0)
        if daily_limit > 0 and _day["count"] >= daily_limit:
            return False
        q = _visitors.setdefault(visitor, deque())
        while q and now - q[0] > PER_VISITOR_WINDOW:
            q.popleft()
        if len(q) >= PER_VISITOR:
            return False
        q.append(now)
        _day["count"] += 1
        if len(_visitors) > 5000:  # forget idle visitors
            for k in [k for k, v in _visitors.items() if not v or now - v[-1] > PER_VISITOR_WINDOW]:
                _visitors.pop(k, None)
        return True


def reset() -> None:
    with _lock:
        _visitors.clear()
        _day.update(date="", count=0)
