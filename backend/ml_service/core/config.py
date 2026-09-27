from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ml_service/core/config.py -> backend/ml_service/.env
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / "ml_service" / ".env"


_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_ARTIFACTS = str(_BACKEND_DIR / "artifacts") if (_BACKEND_DIR / "artifacts").exists() else "artifacts"


class Settings(BaseSettings):
    """Configuration for the ML Inference Service.

    Kept deliberately separate from app_service's Settings (even though
    the shape looks similar) -- per the approved architecture, the two
    services are independently deployable and must never share a config
    object or a process, only the ml_common library.
    """

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "Scam Detection ML Inference Service"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    ARTIFACTS_DIR: str = _DEFAULT_ARTIFACTS
    PRODUCTION_MODEL_NAME: str = "naive_bayes"

    RATE_LIMIT_DEFAULT: str = "200/minute"
    RATE_LIMIT_PREDICT: str = "60/minute"

    LOG_LEVEL: str = "INFO"

    # CORS is intentionally NOT configured here: this service is only
    # ever called internally (app_service -> ml_service), never directly
    # from a browser, per the approved architecture's internal-only
    # /internal/v1/predict endpoint design.


@lru_cache
def get_settings() -> Settings:
    return Settings()
