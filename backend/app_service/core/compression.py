"""Gzip for API responses, except the Copilot's server-sent-event stream.

History responses are ~380 KB of JSON (each scan carries its X-Ray and
TrustLens report) and compress about 30x. Starlette's GZipMiddleware would
also buffer the event stream and delay the Copilot's live answer, so that one
path is passed through untouched."""

from starlette.middleware.gzip import GZipMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

STREAMING_PATHS = ("/api/v1/copilot/chat",)


class SelectiveGZipMiddleware:
    def __init__(self, app: ASGIApp, minimum_size: int = 1000) -> None:
        self.app = app
        self.gzip = GZipMiddleware(app, minimum_size=minimum_size)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and not scope.get("path", "").startswith(STREAMING_PATHS):
            await self.gzip(scope, receive, send)
        else:
            await self.app(scope, receive, send)
