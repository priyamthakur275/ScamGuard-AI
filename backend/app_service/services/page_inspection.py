"""Inspects the page a checked link actually lands on.

The URL itself can look harmless; what gives a phishing page away is what
it asks for. This reads the fetched HTML (never executes it) and reports:
- forms collecting passwords, OTPs, PINs, card numbers, CVV, Aadhaar/PAN, UPI PIN
- forms that submit to a different domain than the page
- a well-known Indian/global brand named on the page while the domain is
  not that brand's official one (impersonation)
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

SENSITIVE = {
    "password": re.compile(r"pass(word|wd)?|pwd", re.I),
    "OTP": re.compile(r"\botp\b|one.?time", re.I),
    "PIN": re.compile(r"\b(m?pin|upi.?pin|atm.?pin)\b", re.I),
    "card number": re.compile(r"card.?(no|num)|cc.?num|debit|credit", re.I),
    "CVV": re.compile(r"cvv|cvc|security.?code", re.I),
    "Aadhaar / PAN": re.compile(r"aadhaa?r|\bpan\b", re.I),
    "net banking login": re.compile(r"user.?id|customer.?id|login.?id", re.I),
}

# brand -> official registrable domains
BRANDS = {
    "SBI": ("sbi.co.in", "onlinesbi.sbi", "sbi.bank.in", "onlinesbi.com"),
    "HDFC Bank": ("hdfcbank.com", "hdfc.bank.in"),
    "ICICI Bank": ("icicibank.com", "icici.bank.in"),
    "Axis Bank": ("axisbank.com", "axis.bank.in"),
    "Paytm": ("paytm.com",),
    "PhonePe": ("phonepe.com",),
    "Google Pay": ("google.com", "pay.google.com"),
    "Amazon": ("amazon.in", "amazon.com"),
    "Flipkart": ("flipkart.com",),
    "India Post": ("indiapost.gov.in",),
    "Income Tax Department": ("incometax.gov.in",),
    "UIDAI / Aadhaar": ("uidai.gov.in",),
    "Netflix": ("netflix.com",),
    "Microsoft": ("microsoft.com", "live.com", "office.com"),
    "Apple": ("apple.com", "icloud.com"),
    "WhatsApp": ("whatsapp.com",),
}
_BRAND_RX = {b: re.compile(r"\b" + re.escape(b.split(" /")[0]) + r"\b", re.I) for b in BRANDS}


def _host(url: str) -> str:
    h = (urlparse(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def _belongs(host: str, domains: tuple[str, ...]) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


def inspect_page(soup, final_url: str) -> dict:
    host = _host(final_url)
    findings: list[dict] = []
    asked: set[str] = set()
    external_posts: set[str] = set()

    for form in soup.find_all("form"):
        action = form.get("action") or final_url
        target = _host(urljoin(final_url, action))
        fields = form.find_all(["input", "select", "textarea"])
        for f in fields:
            descriptor = " ".join(str(f.get(a, "")) for a in ("name", "id", "placeholder", "aria-label", "autocomplete"))
            if (f.get("type") or "").lower() == "password":
                asked.add("password")
            for label, rx in SENSITIVE.items():
                if rx.search(descriptor):
                    asked.add(label)
        if fields and target and target != host:
            external_posts.add(target)

    # Inputs outside <form> (JS-submitted pages) count too.
    for f in soup.find_all("input"):
        if (f.get("type") or "").lower() == "password":
            asked.add("password")

    if asked:
        findings.append({
            "code": "collects_sensitive_data",
            "severity": "high" if asked & {"OTP", "PIN", "CVV", "card number", "password"} else "medium",
            "reason": f"The page has a form asking for: {', '.join(sorted(asked))}.",
        })
    if external_posts:
        findings.append({
            "code": "form_posts_elsewhere",
            "severity": "high",
            "reason": f"Form data is sent to a different site: {', '.join(sorted(external_posts))}.",
        })

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    visible = f"{title} {soup.get_text(' ', strip=True)[:4000]}"
    impersonated = None
    for brand, rx in _BRAND_RX.items():
        if rx.search(visible) and not _belongs(host, BRANDS[brand]):
            impersonated = brand
            break
    if impersonated and (asked or external_posts):
        findings.append({
            "code": "brand_impersonation",
            "severity": "high",
            "reason": f"The page presents itself as {impersonated}, but {host} is not an official {impersonated} domain.",
        })

    return {
        "final_host": host,
        "title": title[:200],
        "sensitive_fields": sorted(asked),
        "form_posts_to": sorted(external_posts),
        "impersonated_brand": impersonated if (asked or external_posts) else None,
        "findings": findings,
    }


def evidence_lines(report: dict) -> list[str]:
    """Plain-text lines appended to the analysed text so the risk engine sees them."""
    lines = []
    if report.get("sensitive_fields"):
        lines.append(f"Page inspection: the page collects {', '.join(report['sensitive_fields'])}.")
    if report.get("form_posts_to"):
        lines.append(f"Page inspection: form submits to another site ({', '.join(report['form_posts_to'])}).")
    if report.get("impersonated_brand"):
        lines.append(f"Page inspection: impersonates {report['impersonated_brand']} on an unofficial domain.")
    return lines
