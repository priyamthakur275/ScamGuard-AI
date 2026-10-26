from starlette.requests import Request

from app_service.core.rate_limit import get_client_ip


def _req(headers: dict[str, str]) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw, "client": ("10.0.0.9", 1234)})


def test_prefers_frontend_forwarded_client_ip():
    assert get_client_ip(_req({"x-scamguard-client-ip": "49.1.2.3", "x-forwarded-for": "10.1.1.1"})) == "49.1.2.3"


def test_falls_back_to_x_forwarded_for_then_socket():
    assert get_client_ip(_req({"x-forwarded-for": "49.9.9.9, 10.1.1.1"})) == "49.9.9.9"
    assert get_client_ip(_req({})) == "10.0.0.9"


def test_health_is_never_rate_limited(client):
    for _ in range(320):
        assert client.get("/api/v1/health").status_code == 200


def test_rate_limits_off_for_local_development_only():
    from app_service.core.config import Settings
    assert Settings(APP_ENV="development").rate_limit_enabled is False
    assert Settings(APP_ENV="local").rate_limit_enabled is False
    assert Settings(APP_ENV="test").rate_limit_enabled is True
    assert Settings(APP_ENV="production", SECRET_KEY="x" * 40).rate_limit_enabled is True
    assert Settings(APP_ENV="development", RATE_LIMIT_ENABLED=True).rate_limit_enabled is True


def test_no_separate_ml_service_by_default():
    from app_service.core.config import Settings
    assert Settings(_env_file=None).ML_SERVICE_URL == ""
