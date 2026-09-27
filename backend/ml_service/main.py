from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from ml_service.api.deps import build_inference_engine
from ml_service.api.v1.router import api_router
from ml_service.core.config import get_settings
from ml_service.core.exception_handlers import register_exception_handlers
from ml_service.core.logging_config import configure_logging, get_logger
from ml_service.core.rate_limit import limiter

configure_logging()
settings = get_settings()
logger = get_logger("ml_service.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Model loading happens once, at process startup -- not per request --
    # so the hot prediction path never touches disk. If no production
    # model is registered yet, the service still starts (so /health stays
    # green for the orchestrator) but /ready reports not-ready and
    # /predict returns 503 until a model is trained and promoted.
    engine = build_inference_engine()
    try:
        engine.load()
        logger.info(
            f"Loaded production model '{engine.version_info.model_name}' "
            f"version '{engine.version_info.version}'"
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"No production model loaded at startup: {exc}")

    app.state.inference_engine = engine
    yield


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)

# --- Rate limiting -----------------------------------------------------
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": "Too many requests, please try again later",
        },
    )


app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# --- Global exception handling --------------------------------------------
register_exception_handlers(app)

# --- Routes ----------------------------------------------------------------
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
