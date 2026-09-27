from slowapi import Limiter
from starlette.requests import Request

from ml_service.core.config import get_settings

settings = get_settings()


def get_client_ip(request: Request) -> str:
    """Resolve the real client IP for rate limiting.

    Identical rationale to app_service/core/rate_limit.py: ml_service is
    only ever reached through a proxy (the frontend's same-origin
    rewrite, since ml_service has no CORS support by design), so the raw
    connection address is always the proxy's IP, not the real caller's.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=get_client_ip, default_limits=[settings.RATE_LIMIT_DEFAULT])
