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
