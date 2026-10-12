from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app_service.services import domain_trust as dt


def _rdap(days_old: int) -> dict:
    when = (datetime.now(timezone.utc) - timedelta(days=days_old)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "events": [{"eventAction": "registration", "eventDate": when}],
        "entities": [{"roles": ["registrar"], "vcardArray": ["vcard", [["fn", {}, "text", "Example Registrar"]]]}],
    }


@pytest.mark.live_rdap
def test_lookup_parses_age_and_registrar_and_caches():
    dt._CACHE.clear()
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(200, json=_rdap(12))

    r = dt.lookup_domain_age("new-scam-shop.xyz", transport=httpx.MockTransport(handler))
    assert r["age_days"] == 12 and r["registrar"] == "Example Registrar"
    dt.lookup_domain_age("new-scam-shop.xyz", transport=httpx.MockTransport(handler))
    assert len(calls) == 1  # cached


@pytest.mark.live_rdap
def test_lookup_failure_means_unknown_not_error():
    dt._CACHE.clear()
    boom = httpx.MockTransport(lambda r: (_ for _ in ()).throw(httpx.ConnectError("down")))
    assert dt.lookup_domain_age("example.com", transport=boom) is None
    assert dt.lookup_domain_age("192.168.0.1") is None


def test_trust_score_bands():
    young = dt.trust_score({"scheme": "http", "evidence": [{"severity": "medium"}]}, {"age_days": 5}, {"sensitive_fields": ["OTP"]})
    old = dt.trust_score({"scheme": "https", "evidence": [], "tls": {"is_expired": False}}, {"age_days": 3650}, None)
    assert young["band"] == "untrustworthy" and young["score"] < 20
    assert old["band"] == "trustworthy" and old["score"] >= 85
    assert all("label" in f and "impact" in f for f in young["factors"])


def test_new_domain_raises_the_scam_score():
    from ml_service.inference.threat_scorer import ThreatScorer
    text = "URL: https://shop-offer.in\n" + dt.evidence_line({"age_days": 6})
    plain = "URL: https://shop-offer.in"
    s = ThreatScorer()
    assert s.assess(0.3, text.lower().split(), text).threat_score > s.assess(0.3, plain.lower().split(), plain).threat_score
