"""Website trust score for checked links.

Domain age is the single strongest public signal for scam websites: most
phishing and fake-shop domains are days or weeks old. Age comes from RDAP
(the official successor to WHOIS, run by the domain registries) through
the rdap.org bootstrap service. The lookup is best-effort: a short
timeout, cached for a day, and a failure simply means "age unknown".

The trust score is a transparent 0-100 sum of documented factors (no
model), so every point can be explained.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx

RDAP_URL = "https://rdap.org/domain/{domain}"
_CACHE: dict[str, tuple[float, dict | None]] = {}
_TTL = 24 * 3600


def _parse_rdap(data: dict) -> dict | None:
    registered = None
    for event in data.get("events", []) or []:
        if event.get("eventAction") == "registration" and event.get("eventDate"):
            registered = event["eventDate"]
            break
    if not registered:
        return None
    try:
        dt = datetime.fromisoformat(registered.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    registrar = None
    for ent in data.get("entities", []) or []:
        if "registrar" in (ent.get("roles") or []):
            for item in (ent.get("vcardArray") or [None, []])[1]:
                if isinstance(item, list) and item and item[0] == "fn":
                    registrar = item[3]
            break
    age_days = max(0, (datetime.now(timezone.utc) - dt).days)
    return {"registered_on": dt.date().isoformat(), "age_days": age_days, "registrar": registrar}


def lookup_domain_age(domain: str, transport: httpx.BaseTransport | None = None) -> dict | None:
    domain = (domain or "").strip().lower().rstrip(".")
    if not domain or "." not in domain or domain.replace(".", "").isdigit():
        return None
    cached = _CACHE.get(domain)
    if cached and time.monotonic() - cached[0] < _TTL:
        return cached[1]
    result = None
    try:
        with httpx.Client(timeout=4.0, follow_redirects=True, transport=transport,
                          headers={"Accept": "application/rdap+json, application/json"}) as client:
            resp = client.get(RDAP_URL.format(domain=domain))
            if resp.status_code == 200:
                result = _parse_rdap(resp.json())
    except Exception:
        result = None
    _CACHE[domain] = (time.monotonic(), result)
    return result


def trust_score(url_intel: dict, domain_age: dict | None, page_report: dict | None) -> dict:
    score = 60
    factors: list[dict] = []

    def add(label: str, impact: int) -> None:
        nonlocal score
        score += impact
        factors.append({"label": label, "impact": impact})

    if domain_age:
        days = domain_age["age_days"]
        if days < 30:
            add(f"Domain registered only {days} days ago", -35)
        elif days < 180:
            add(f"Domain is young ({days} days old)", -15)
        elif days >= 5 * 365:
            add(f"Domain has existed for {days // 365} years", 25)
        elif days >= 365:
            add(f"Domain has existed for {days // 365} year(s)", 15)
        else:
            add(f"Domain is {days // 30} months old", 5)
    else:
        factors.append({"label": "Registration date not available", "impact": 0})

    tls = url_intel.get("tls") or {}
    if url_intel.get("scheme") == "http":
        add("No HTTPS encryption", -10)
    elif tls.get("is_expired") is True:
        add("Security certificate has expired", -20)
    elif url_intel.get("scheme") == "https":
        add("Uses HTTPS", 5)

    penalty = 0
    for signal in url_intel.get("evidence") or []:
        penalty += {"high": 20, "medium": 10, "low": 5}.get(signal.get("severity"), 0)
    if penalty:
        add(f"{len(url_intel.get('evidence') or [])} suspicious link signal(s)", -min(penalty, 40))

    page = page_report or {}
    if page.get("sensitive_fields"):
        add("Page asks for " + ", ".join(page["sensitive_fields"]), -20)
    if page.get("form_posts_to"):
        add("Form sends data to another site", -20)
    if page.get("impersonated_brand"):
        add(f"Pretends to be {page['impersonated_brand']}", -25)

    score = max(0, min(100, score))
    band = "trustworthy" if score >= 75 else "caution" if score >= 45 else "untrustworthy"
    return {"score": score, "band": band, "factors": factors}


def evidence_line(domain_age: dict | None) -> str | None:
    if domain_age and domain_age["age_days"] < 180:
        return f"- Domain was registered {domain_age['age_days']} days ago; new domains are often used for scams."
    return None
