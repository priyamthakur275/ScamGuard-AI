from slowapi import Limiter
from starlette.requests import Request

from app_service.core.config import get_settings

settings = get_settings()


def get_client_ip(request: Request) -> str:
    """Resolve the real client IP for rate limiting.

    Every request now arrives via a reverse proxy (the frontend's Next.js
    server, Vercel's edge network, or self-hosted Nginx) rather than
    directly from the browser, so the raw connection address
    (slowapi's default get_remote_address) is always the proxy's IP --
    which would put every real user behind the proxy into the same
    rate-limit bucket. Trust the standard X-Forwarded-For header (set by
    all three of those proxies) instead, falling back to the connection
    address only if it's absent (e.g. direct/local development traffic).
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=get_client_ip, default_limits=[settings.RATE_LIMIT_DEFAULT])
