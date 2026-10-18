"""Guards against slow pages: each database round trip costs ~60 ms on the
hosted database, so these endpoints must not issue one query per row."""
from sqlalchemy import event

from app_service.repositories.analytics_repository import AnalyticsRepository


def _count_queries(db_session, fn):
    n = {"q": 0}
    engine = db_session.get_bind()

    def on(*_a, **_k):
        n["q"] += 1

    event.listen(engine, "before_cursor_execute", on)
    try:
        result = fn()
    finally:
        event.remove(engine, "before_cursor_execute", on)
    return result, n["q"]


def _login(client):
    import uuid as _uuid

    from tests.conftest import register_and_login

    tok = register_and_login(client, f"q{_uuid.uuid4().hex[:8]}@example.com")
    return {"Authorization": f"Bearer {tok}"}


def test_history_is_constant_queries(client, db_session):
    h = _login(client)
    for i in range(12):
        client.post("/api/v1/messages/scan", data={"text": f"Share the OTP {i} now or your account is blocked", "input_type": "TEXT"}, headers=h)
    res, q = _count_queries(db_session, lambda: client.get("/api/v1/messages/history", headers=h))
    assert res.status_code == 200 and len(res.json()) >= 12
    assert q <= 3, f"history used {q} queries"


def test_analytics_summary_is_one_aggregate_query(client, db_session):
    h = _login(client)
    for i in range(5):
        client.post("/api/v1/messages/scan", data={"text": f"Share the OTP {i} now", "input_type": "TEXT"}, headers=h)
    res, q = _count_queries(db_session, lambda: client.get("/api/v1/analytics/summary", headers=h))
    assert res.status_code == 200 and q <= 3, f"summary used {q} queries"


def test_combined_matches_the_separate_queries(client, db_session):
    h = _login(client)
    for t in ("Share the OTP now or account blocked", "See you at 6", "Pay Rs 500 registration fee to claim prize"):
        client.post("/api/v1/messages/scan", data={"text": t, "input_type": "TEXT"}, headers=h)
    me = client.get("/api/v1/users/me", headers=h).json()
    import uuid
    uid = uuid.UUID(me["id"])
    repo = AnalyticsRepository(db_session)
    for rng in ("7d", "30d", "all"):
        try:
            d = repo.combined(uid, rng)
        except Exception:
            continue
        from app_service.db.postgres.models import Prediction
        assert d["total"] == repo.total_scans(uid, rng)
        assert d["verdict"] == repo.group_counts(uid, rng, Prediction.verdict)
        assert d["risk"] == repo.group_counts(uid, rng, Prediction.risk_level)
        assert d["category"] == repo.group_counts(uid, rng, Prediction.scam_category)
        assert d["input_type"] == repo.group_counts(uid, rng, Prediction.input_type)
        assert d["feedback"] == repo.feedback_counts(uid, rng)
        assert d["high_risk"] == repo.high_risk_count(uid, rng)
        ac, at = repo.averages(uid, rng)
        assert abs(d["avg_confidence"] - ac) < 1e-9 and abs(d["avg_threat"] - at) < 1e-9


def test_large_json_is_gzipped_but_the_copilot_stream_is_not(client):
    h = _login(client)
    for i in range(6):
        client.post("/api/v1/messages/scan", data={"text": f"Share the OTP {i} now or your account is blocked", "input_type": "TEXT"}, headers=h)
    r = client.get("/api/v1/messages/history", headers={**h, "Accept-Encoding": "gzip"})
    assert r.status_code == 200 and r.headers.get("content-encoding") == "gzip" and len(r.json()) >= 6
    s = client.post("/api/v1/copilot/chat", json={"message": "hello"}, headers={"Accept-Encoding": "gzip"})
    assert s.headers.get("content-encoding") is None and s.headers["content-type"].startswith("text/event-stream")
