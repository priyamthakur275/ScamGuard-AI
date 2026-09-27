import pytest
from pydantic import ValidationError

from app_service.core.config import Settings

KNOWN_DEFAULT_SECRET = "scamguard_development_secret_key_minimum_32_chars_123456789"


class TestSecretKeySafetyGuard:
    def test_refuses_to_start_with_default_secret_when_debug_false(self):
        with pytest.raises(ValidationError, match="publicly-known development default"):
            Settings(DEBUG=False, SECRET_KEY=KNOWN_DEFAULT_SECRET)

    def test_allows_default_secret_when_debug_true(self):
        # Local development convenience: DEBUG=true is the explicit signal
        # that this is not a real deployment.
        settings = Settings(DEBUG=True, SECRET_KEY=KNOWN_DEFAULT_SECRET)
        assert settings.SECRET_KEY == KNOWN_DEFAULT_SECRET

    def test_allows_a_real_secret_when_debug_false(self):
        settings = Settings(DEBUG=False, SECRET_KEY="a-real-random-secret-that-is-at-least-32-chars-long")
        assert settings.DEBUG is False

    def test_debug_defaults_to_false(self, monkeypatch):
        # Regression test for the actual production gap this closes:
        # render.yaml never sets DEBUG, so whatever this class-level
        # default is IS what runs in production. It must be False.
        # This test suite's own conftest.py sets DEBUG=true in the process
        # environment (for convenient local test runs), and _env_file=None
        # only skips the .env FILE, not OS env vars -- so both have to be
        # bypassed here to see the actual code-level default in isolation.
        monkeypatch.delenv("DEBUG", raising=False)
        settings = Settings(_env_file=None, SECRET_KEY="a-real-random-secret-that-is-at-least-32-chars-long")
        assert settings.DEBUG is False
