from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app_service/core/config.py -> backend/.env
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"

# Local SQLite fallback for development when PostgreSQL is unavailable.
_DEFAULT_SQLITE_DB = Path(__file__).resolve().parent.parent / "scam_detection.db"


class Settings(BaseSettings):
    """Single source of truth for all runtime configuration.

    Values are read from environment variables first, falling back to a
    local `.env` file. See `.env.example` for the full list of supported
    keys and their meaning.
    """

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "Scam Detection Application Service"

    # Public demo account (one-click "Try the demo account" on the sign-in
    # page). Its password is random and never used; access is only through
    # POST /auth/demo-login, and profile/password/delete actions are blocked.
    DEMO_ACCOUNT_ENABLED: bool = True
    DEMO_ACCOUNT_EMAIL: str = "demo@scamguard.app"
    # Accounts that also receive the 15 sample scans once (comma separated).
    SAMPLE_SCAN_EMAILS: str = "priyamthakur275@gmail.com"
    APP_ENV: str = "development"
    # SECURITY: defaults to False deliberately. Starlette's debug mode can
    # surface internal tracebacks for errors that occur outside our own
    # exception handlers (e.g. in middleware, before routing). This used to
    # default to True -- and render.yaml (the actual production deploy)
    # never overrides it -- meaning production was silently running in
    # debug mode. Local development opts in explicitly via backend/.env
    # (see .env.example, DEBUG=true there).
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    _DEFAULT_SECRET_KEY: str = "scamguard_development_secret_key_minimum_32_chars_123456789"

    # Security / JWT
    SECRET_KEY: str = Field(
        default="scamguard_development_secret_key_minimum_32_chars_123456789",
        min_length=32,
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @model_validator(mode="after")
    def _refuse_known_default_secret_outside_debug(self) -> "Settings":
        # The hardcoded SECRET_KEY above exists purely so a fresh local
        # checkout runs with zero config. It is PUBLIC (it's committed
        # source code) -- anyone can read it and forge valid JWTs,
        # including admin-role tokens, for any deployment that ends up
        # running with it. DEBUG=true is treated as "this is a local dev
        # run" and is allowed to use it for convenience; anything else
        # (DEBUG=false, i.e. every real deployment target) must not be
        # allowed to silently start with a secret an attacker can read on
        # GitHub. Fail loudly at startup instead.
        if not self.DEBUG and self.SECRET_KEY == self._DEFAULT_SECRET_KEY:
            raise ValueError(
                "SECRET_KEY is still set to the publicly-known development default "
                "while DEBUG=false. Set a real SECRET_KEY (e.g. "
                "`python -c \"import secrets; print(secrets.token_urlsafe(48))\"`) "
                "before running outside local development."
            )
        return self

    # Database
    # Local development can use sqlite if PostgreSQL is unavailable.
    DATABASE_URL: str = f"sqlite:///{_DEFAULT_SQLITE_DB}"

    # Internal service-to-service URL for calling ml_service
    ML_SERVICE_URL: str = "http://localhost:8002"

    # Voice transcription (Phase 6): no provider is configured by default.
    # When unset, server-side audio-file transcription is honestly
    # reported as unavailable rather than faked -- see
    # voice_transcription.py. Browser-side live transcription (Web Speech
    # API) works regardless of this setting, since it never touches the
    # backend.
    VOICE_TRANSCRIPTION_PROVIDER: str | None = None
    VOICE_TRANSCRIPTION_API_KEY: str | None = None

    # ScamGuard Copilot (Phase 17): same pattern -- no LLM provider
    # configured by default, so Copilot answers via the deterministic,
    # evidence-grounded engine (copilot_service.py) instead of an
    # external LLM. See copilot_llm_provider.py.
    COPILOT_LLM_PROVIDER: str | None = None
    COPILOT_LLM_API_KEY: str | None = None
    COPILOT_LLM_MODEL: str | None = None  # optional override of the provider's default model

    # CORS
    #
    # Deliberately a plain str, NOT List[str]. pydantic-settings treats
    # List[...] as a "complex" type and attempts to json.loads() any
    # value read from a .env file or environment variable for such
    # fields BEFORE any Pydantic field_validator runs. A value like
    # "http://localhost:3000" is not valid JSON, so that json.loads()
    # call raises pydantic_settings.SettingsError and crashes the
    # application on startup -- every time, for every developer who
    # follows .env.example, regardless of any other configuration.
    # Storing this as a str (a "simple" type, never JSON-decoded) and
    # parsing it ourselves via the property below avoids the bug
    # entirely.
    CORS_ORIGINS: str = "http://localhost:3000,https://frontend-psi-ebon-83.vercel.app"

    # Rate limiting
    # Per visitor IP. A whole classroom/office can share one public IP
    # (NAT), so limits are sized for a room of people, not one person.
    RATE_LIMIT_DEFAULT: str = "300/minute"

    # Keep-alive (see services/keep_alive.py). Production only.
    KEEPALIVE_ENABLED: bool = True
    KEEPALIVE_URL: str = "https://scamguard-frontend-r6t7.onrender.com/backend-api/api/v1/health"
    KEEPALIVE_WINDOW_IST: str = "07:00-23:00"
    RATE_LIMIT_AUTH: str = "10/minute"

    # ---- Logging ----
    LOG_LEVEL: str = "INFO"

    # ---- OCR ----
    TESSERACT_CMD: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def get_sqlalchemy_database_url(self) -> str:
        if self.DATABASE_URL.startswith("postgres://"):
            return self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return self.DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor. Settings are read once per process."""
    return Settings()
