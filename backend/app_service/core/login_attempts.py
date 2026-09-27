"""Tracks failed login attempts per email, in-process, to decide when a
login attempt must additionally pass a CAPTCHA challenge.

LIMITATION (documented, not hidden): this is an in-memory counter. It
resets whenever the process restarts and is NOT shared across multiple
app_service instances/replicas. That is an acceptable simplification for
a single-instance deployment (which is what this project actually runs,
see render.yaml) but would need to move to something shared (Redis, or a
DB table) before running more than one instance. It is not pretended to
be more than that.
"""
import threading
import time

CAPTCHA_REQUIRED_AFTER_FAILURES = 3
ATTEMPT_WINDOW_SECONDS = 15 * 60

_lock = threading.Lock()
_failures: dict[str, list[float]] = {}


def _prune(email: str, now: float) -> None:
    attempts = _failures.get(email, [])
    _failures[email] = [t for t in attempts if now - t < ATTEMPT_WINDOW_SECONDS]
    if not _failures[email]:
        _failures.pop(email, None)


def record_failure(email: str) -> None:
    email = email.lower()
    now = time.time()
    with _lock:
        _prune(email, now)
        _failures.setdefault(email, []).append(now)


def record_success(email: str) -> None:
    email = email.lower()
    with _lock:
        _failures.pop(email, None)


def captcha_required(email: str) -> bool:
    email = email.lower()
    now = time.time()
    with _lock:
        _prune(email, now)
        return len(_failures.get(email, [])) >= CAPTCHA_REQUIRED_AFTER_FAILURES


def reset_all() -> None:
    """Test-only helper to reset state between tests."""
    with _lock:
        _failures.clear()
