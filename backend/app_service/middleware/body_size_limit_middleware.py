from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Generous for every JSON payload this API actually accepts (the largest
# is AnalyzeRequest.text, capped at 5000 chars by its own schema -- a few
# KB even with headers/other fields). Deliberately NOT applied to
# multipart/form-data (file uploads): those already have their own
# dedicated, larger limit (MAX_UPLOAD_BYTES in extraction.py, checked once
# the file is actually read) sized for real images/PDFs, and enforcing
# this same small cap there would break legitimate uploads.
JSON_BODY_LIMIT_BYTES = 256 * 1024  # 256 KB
MULTIPART_BODY_LIMIT_BYTES = 16 * 1024 * 1024  # 16 MB, defense-in-depth above the 8MB file cap


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects requests whose declared Content-Length exceeds a sane cap,
    before Starlette reads the body into memory.

    KNOWN LIMITATION: this checks the Content-Length header, which is only
    present for non-chunked requests -- FastAPI's TestClient (and every
    normal HTTP client used by this app's own frontend) always sends it,
    so this closes the realistic case. A request sent with
    Transfer-Encoding: chunked and no Content-Length would not be caught
    here; closing that fully would require wrapping the ASGI receive
    channel to enforce a running byte cap while streaming, which risks
    interfering with the existing multipart file-upload streaming path if
    implemented incorrectly. Documented here rather than shipped
    unverified.
    """

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                declared_size = None

            if declared_size is not None:
                content_type = request.headers.get("content-type", "")
                limit = (
                    MULTIPART_BODY_LIMIT_BYTES
                    if content_type.startswith("multipart/form-data")
                    else JSON_BODY_LIMIT_BYTES
                )
                if declared_size > limit:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error_code": "PAYLOAD_TOO_LARGE",
                            "message": f"Request body exceeds the {limit // 1024} KB limit for this request type.",
                        },
                    )

        return await call_next(request)
