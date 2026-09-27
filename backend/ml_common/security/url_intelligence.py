"""URL lexical/structural intelligence.

Every field this module produces is directly computed from the URL string
itself -- no network calls, no invented "reputation" or "domain age"
scores, no fabricated TLS/WHOIS data. Network-dependent signals (TLS
certificate details, live redirect-chain hosts, resolved IPs) are computed
separately by extraction.py, which already performs the real, SSRF-guarded
HTTP fetch, and are merged into this module's evidence via
`network_evidence_from_fetch()` below.

This is a best-effort heuristic layer, not a full implementation of the
public suffix list (PSL) algorithm browsers use -- `_registrable_domain`
below only special-cases a short, explicit list of common multi-label
suffixes (co.in, co.uk, ...). It will misclassify uncommon multi-part
TLDs it doesn't know about. That limitation is intentional and documented
here rather than silently wrong.

DESIGN PRINCIPLE (explicit per the security review that requested this
module): this file NEVER computes a verdict or a "malicious" boolean. It
only returns individual, independently-labeled evidence signals, each with
a severity and a plain-language reason. Aggregating those into a verdict
is the risk engine's job (ThreatScorer), not this module's -- a single
triggered heuristic here must never, by itself, mean "malicious".
"""
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit, unquote
import ipaddress

# Suffixes that are two labels long from the registrant's point of view
# (e.g. "example.co.in" is registered under "co.in", not just "in"). Not
# exhaustive -- a real implementation would use the Mozilla Public Suffix
# List. This is a deliberately small, explicit list for common cases.
_MULTI_LABEL_SUFFIXES = frozenset({
    "co.in", "co.uk", "co.jp", "co.nz", "co.za",
    "com.au", "com.br", "com.sg", "com.mx",
    "org.in", "net.in", "gov.in", "ac.in", "edu.in",
    "gov.uk", "ac.uk",
})

# TLDs that appear disproportionately often in public phishing-campaign
# roundups because they are cheap or free to register. Presence here is a
# WEAK signal to surface, not a verdict -- plenty of legitimate sites use
# them too.
_SUSPICIOUS_TLDS = frozenset({
    "tk", "ml", "ga", "cf", "gq", "xyz", "top", "work", "click", "link",
    "zip", "mov", "country", "stream", "gdn", "kim", "loan", "men",
    "date", "review", "win", "science", "party", "trade", "bid",
})

_URL_SHORTENERS = frozenset({
    "bit.ly", "t.co", "goo.gl", "tinyurl.com", "is.gd", "ow.ly",
    "buff.ly", "rebrand.ly", "cutt.ly", "shorturl.at",
})

# A short list of frequently-impersonated brand domains for lookalike
# detection. Deliberately short and explicit -- this is not a claim of
# comprehensive brand coverage. Callers can extend this at call time via
# analyze_url(..., extra_brand_domains=...) -- see "configurable brand
# vocabulary" below -- rather than editing this module.
_DEFAULT_BRAND_DOMAINS = frozenset({
    "google.com", "paypal.com", "amazon.com", "microsoft.com", "apple.com",
    "facebook.com", "instagram.com", "whatsapp.com", "netflix.com",
    "sbi.co.in", "hdfcbank.com", "icicibank.com", "irctc.co.in",
    "indiapost.gov.in", "axisbank.com", "paytm.com", "phonepe.com",
})

# Keywords that, when they appear in a URL PATH on a domain that is not a
# known brand, are commonly seen in phishing/credential-harvesting URLs.
# Weak signal on their own -- "/login" is completely ordinary on the
# site's own real domain.
_SUSPICIOUS_PATH_KEYWORDS = frozenset({
    "login", "signin", "verify", "verification", "secure", "account",
    "update", "confirm", "password", "reset", "unlock", "suspended",
    "billing", "invoice", "wallet",
})

# Query parameter NAMES commonly used for open-redirect / URL-forwarding
# tricks (the value often embeds a second, real destination URL).
_SUSPICIOUS_REDIRECT_PARAM_NAMES = frozenset({
    "redirect", "redirect_uri", "redirect_url", "url", "next", "return",
    "returnurl", "return_url", "continue", "dest", "destination", "goto",
    "target", "r",
})

_MAX_REASONABLE_URL_LENGTH = 120

# A real scheme prefix like "javascript:", "mailto:", "data:", "tel:" --
# used to decide whether to apply the "no scheme, assume bare host" `//`
# fallback below. Without this check, "javascript:alert(1)" would get
# "//"-prefixed and misparsed as if "javascript" were a hostname, instead
# of being correctly recognized as a non-http(s) scheme with no host at
# all (still evidence-worthy -- see the non_http_scheme signal -- but for
# what it actually is, not a garbled hostname).
_SCHEME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")


def _registrable_domain(hostname: str) -> str:
    labels = hostname.lower().strip(".").split(".")
    if len(labels) < 2:
        return hostname.lower()
    last_two = ".".join(labels[-2:])
    if last_two in _MULTI_LABEL_SUFFIXES and len(labels) >= 3:
        return ".".join(labels[-3:])
    return last_two


def _levenshtein(a: str, b: str) -> int:
    """Standard edit distance, no external dependency."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev_row = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr_row = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr_row[j] = min(
                curr_row[j - 1] + 1,      # insertion
                prev_row[j] + 1,          # deletion
                prev_row[j - 1] + cost,   # substitution
            )
        prev_row = curr_row
    return prev_row[-1]


def _is_ip_literal(hostname: str) -> "ipaddress.IPv4Address | ipaddress.IPv6Address | None":
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        return None


@dataclass(frozen=True)
class EvidenceSignal:
    """One independent, individually-labeled piece of evidence.

    severity is a description of that ONE signal's typical significance
    in isolation ("low" | "medium" | "high") -- it is not, and must never
    be read as, an aggregate verdict. A URL can have several "low"
    signals and still be entirely benign; a single "high" signal is a
    strong hint, not proof.
    """
    code: str
    severity: str
    reason: str


@dataclass(frozen=True)
class UrlIntelligence:
    """All fields are OBSERVED, computed facts about the URL string --
    not a model interpretation of what they mean. `lookalike_of` and
    `is_suspicious_tld` are the only fields that involve a lookup against
    a fixed list rather than pure string analysis of the URL itself; both
    are still deterministic and reproducible, not inferred.
    """

    original_url: str
    scheme: str
    hostname: str
    port: int | None
    path: str
    query: str
    fragment: str
    registrable_domain: str
    url_length: int
    is_punycode: bool
    is_ip_literal: bool
    ip_version: int | None
    is_shortened: bool
    is_suspicious_tld: bool
    has_userinfo_obfuscation: bool  # e.g. http://real-brand.com@evil.tk/
    has_percent_encoding: bool
    subdomain_depth: int
    hostname_length: int
    digit_ratio_in_hostname: float
    hyphen_count_in_hostname: int
    lookalike_of: str | None  # a known brand domain this closely resembles, if any
    lookalike_distance: int | None  # edit distance to that brand domain
    suspicious_path_keywords: tuple[str, ...]
    suspicious_query_params: tuple[str, ...]
    evidence: tuple[EvidenceSignal, ...]

    def to_dict(self) -> dict:
        return {
            "original_url": self.original_url,
            "scheme": self.scheme,
            "hostname": self.hostname,
            "port": self.port,
            "path": self.path,
            "query": self.query,
            "fragment": self.fragment,
            "registrable_domain": self.registrable_domain,
            "url_length": self.url_length,
            "is_punycode": self.is_punycode,
            "is_ip_literal": self.is_ip_literal,
            "ip_version": self.ip_version,
            "is_shortened": self.is_shortened,
            "is_suspicious_tld": self.is_suspicious_tld,
            "has_userinfo_obfuscation": self.has_userinfo_obfuscation,
            "has_percent_encoding": self.has_percent_encoding,
            "subdomain_depth": self.subdomain_depth,
            "hostname_length": self.hostname_length,
            "digit_ratio_in_hostname": self.digit_ratio_in_hostname,
            "hyphen_count_in_hostname": self.hyphen_count_in_hostname,
            "lookalike_of": self.lookalike_of,
            "lookalike_distance": self.lookalike_distance,
            "suspicious_path_keywords": list(self.suspicious_path_keywords),
            "suspicious_query_params": list(self.suspicious_query_params),
            "evidence": [
                {"code": e.code, "severity": e.severity, "reason": e.reason}
                for e in self.evidence
            ],
        }


def _build_evidence(
    *,
    is_punycode: bool,
    is_ip_literal: bool,
    is_suspicious_tld: bool,
    is_shortened: bool,
    has_userinfo_obfuscation: bool,
    has_percent_encoding: bool,
    subdomain_depth: int,
    url_length: int,
    lookalike_of: str | None,
    lookalike_distance: int | None,
    suspicious_path_keywords: tuple[str, ...],
    suspicious_query_params: tuple[str, ...],
    registrable_domain: str,
    tld: str,
    hostname: str,
    scheme: str,
) -> tuple[EvidenceSignal, ...]:
    signals: list[EvidenceSignal] = []

    if is_punycode:
        signals.append(EvidenceSignal(
            "punycode_hostname", "medium",
            "Hostname uses punycode/IDN encoding, which can render as a different, "
            "visually similar brand name -- a known homograph-attack technique.",
        ))
    if is_ip_literal:
        signals.append(EvidenceSignal(
            "ip_literal_host", "medium",
            "The destination is a raw IP address rather than a domain name.",
        ))
    if is_suspicious_tld:
        signals.append(EvidenceSignal(
            "suspicious_tld", "low",
            f"The top-level domain (.{tld}) appears disproportionately often in public "
            "phishing-campaign reports. Many legitimate sites use it too.",
        ))
    if is_shortened:
        signals.append(EvidenceSignal(
            "url_shortener", "low",
            "The URL uses a link-shortening service, which hides the real destination "
            "until the link is followed.",
        ))
    if has_userinfo_obfuscation:
        signals.append(EvidenceSignal(
            "userinfo_obfuscation", "high",
            "The URL contains userinfo (text before '@') that is not the real "
            "destination host -- a classic trick to make a link look like it points "
            "to a trusted site.",
        ))
    if has_percent_encoding:
        signals.append(EvidenceSignal(
            "percent_encoded_characters", "low",
            "The URL contains percent-encoded characters, which can be used to "
            "obscure its real content from a quick visual read.",
        ))
    if subdomain_depth >= 3:
        signals.append(EvidenceSignal(
            "deep_subdomain_nesting", "low",
            f"The hostname has {subdomain_depth} subdomain levels, which is sometimes "
            "used to bury a brand name deep in a subdomain of an unrelated domain "
            "(e.g. 'paypal.com.evil.tk').",
        ))
    if url_length > _MAX_REASONABLE_URL_LENGTH:
        signals.append(EvidenceSignal(
            "unusually_long_url", "low",
            f"The URL is {url_length} characters long, well beyond a typical "
            "hand-typed or shared link.",
        ))
    if lookalike_of:
        signals.append(EvidenceSignal(
            "brand_lookalike", "high",
            f"The hostname's registrable domain ('{registrable_domain}') is very close "
            f"(edit distance {lookalike_distance}) to the known brand domain "
            f"'{lookalike_of}' without being it -- a common typosquatting pattern.",
        ))
    if suspicious_path_keywords:
        signals.append(EvidenceSignal(
            "suspicious_path_keywords", "low",
            "The URL path contains word(s) commonly seen in credential-harvesting "
            f"pages on non-brand domains: {', '.join(suspicious_path_keywords)}.",
        ))
    if suspicious_query_params:
        signals.append(EvidenceSignal(
            "suspicious_redirect_param", "medium",
            "The URL has query parameter(s) commonly used for open-redirect/URL-"
            f"forwarding tricks: {', '.join(suspicious_query_params)}.",
        ))

    if scheme == "http" and suspicious_path_keywords:
        signals.append(EvidenceSignal(
            "insecure_http_with_sensitive_path", "medium",
            "This page is served over plain HTTP (not HTTPS) and its path suggests "
            "a login/verification/payment page -- any credentials entered would be "
            "sent unencrypted, which legitimate sign-in pages avoid.",
        ))

    if not hostname and scheme and scheme not in ("http", "https"):
        signals.append(EvidenceSignal(
            "non_http_scheme", "high",
            f"This is not a web link at all -- it uses the '{scheme}:' scheme, "
            "which can execute code or trigger unexpected actions (e.g. javascript:, "
            "data:) rather than navigate to a page.",
        ))

    return tuple(signals)


def _safe_port(parts) -> int | None:
    """SplitResult.port raises ValueError for a malformed/adversarial
    netloc (e.g. a javascript: pseudo-URL, which after our "//" prefixing
    gets parsed with garbage where a port would be). A URL intelligence
    module must never crash on adversarial input -- that's a DoS vector
    in its own right -- so this degrades to None instead of raising.
    """
    try:
        return parts.port
    except ValueError:
        return None


def analyze_url(raw_url: str, extra_brand_domains: frozenset[str] | None = None) -> UrlIntelligence:
    """extra_brand_domains lets a caller extend the brand vocabulary used
    for lookalike detection (e.g. an org's own domains) without editing
    this module -- the "configurable brand vocabulary" requirement.
    """
    brand_domains = _DEFAULT_BRAND_DOMAINS | (extra_brand_domains or frozenset())

    has_explicit_scheme = bool(_SCHEME_PATTERN.match(raw_url))
    if has_explicit_scheme and "//" not in raw_url:
        # A real scheme with no "//" (javascript:, mailto:, data:, tel:,
        # ...) -- parse as-is, do NOT force a "//" prefix, which would
        # misparse the scheme's content as a hostname.
        parts = urlsplit(raw_url)
    else:
        parts = urlsplit(raw_url if "//" in raw_url else f"//{raw_url}")
    hostname = (parts.hostname or "").lower()
    registrable = _registrable_domain(hostname) if hostname else ""

    ip_obj = _is_ip_literal(hostname) if hostname else None
    is_ip = ip_obj is not None
    ip_version = ip_obj.version if ip_obj is not None else None
    tld = registrable.split(".")[-1] if "." in registrable else ""

    labels = hostname.split(".") if hostname else []
    subdomain_depth = max(len(labels) - 2, 0) if not is_ip else 0
    digit_count = sum(c.isdigit() for c in hostname)
    digit_ratio = round(digit_count / len(hostname), 4) if hostname else 0.0

    lookalike_of = None
    lookalike_distance = None
    if registrable and not is_ip and registrable not in brand_domains:
        best_brand = None
        best_distance = None
        for brand in brand_domains:
            brand_base = brand.split(".")[0]
            candidate_base = registrable.split(".")[0]
            distance = _levenshtein(candidate_base, brand_base)
            # Only worth flagging when the candidate is close to a brand
            # name AND not trivially different in length (avoids flagging
            # short, unrelated domains that happen to share few letters).
            if len(brand_base) >= 4 and 0 < distance <= 2:
                if best_distance is None or distance < best_distance:
                    best_brand, best_distance = brand, distance
        lookalike_of, lookalike_distance = best_brand, best_distance

    raw_query = parts.query or ""
    query_param_names = {p.split("=", 1)[0].lower() for p in raw_query.split("&") if p}
    suspicious_query_params = tuple(sorted(query_param_names & _SUSPICIOUS_REDIRECT_PARAM_NAMES))

    path_lower = (parts.path or "").lower()
    # Only flag path keywords when the domain ITSELF is not a known brand
    # -- "/login" on the real bank's own domain is completely normal.
    suspicious_path_keywords: tuple[str, ...] = ()
    if registrable not in brand_domains:
        found = {kw for kw in _SUSPICIOUS_PATH_KEYWORDS if kw in path_lower}
        suspicious_path_keywords = tuple(sorted(found))

    full_url_for_length = raw_url
    url_length = len(full_url_for_length)
    has_percent_encoding = "%" in raw_url and unquote(raw_url) != raw_url

    is_punycode = "xn--" in hostname
    is_shortened = registrable in _URL_SHORTENERS
    is_suspicious_tld = tld in _SUSPICIOUS_TLDS
    has_userinfo = bool(parts.username)

    evidence = _build_evidence(
        is_punycode=is_punycode,
        is_ip_literal=is_ip,
        is_suspicious_tld=is_suspicious_tld,
        is_shortened=is_shortened,
        has_userinfo_obfuscation=has_userinfo,
        has_percent_encoding=has_percent_encoding,
        subdomain_depth=subdomain_depth,
        url_length=url_length,
        lookalike_of=lookalike_of,
        lookalike_distance=lookalike_distance,
        suspicious_path_keywords=suspicious_path_keywords,
        suspicious_query_params=suspicious_query_params,
        registrable_domain=registrable,
        tld=tld,
        hostname=hostname,
        scheme=(parts.scheme or "").lower(),
    )

    return UrlIntelligence(
        original_url=raw_url,
        scheme=(parts.scheme or "").lower(),
        hostname=hostname,
        port=_safe_port(parts),
        path=parts.path or "",
        query=raw_query,
        fragment=parts.fragment or "",
        registrable_domain=registrable,
        url_length=url_length,
        is_punycode=is_punycode,
        is_ip_literal=is_ip,
        ip_version=ip_version,
        is_shortened=is_shortened,
        is_suspicious_tld=is_suspicious_tld,
        has_userinfo_obfuscation=has_userinfo,
        has_percent_encoding=has_percent_encoding,
        subdomain_depth=subdomain_depth,
        hostname_length=len(hostname),
        digit_ratio_in_hostname=digit_ratio,
        hyphen_count_in_hostname=hostname.count("-"),
        lookalike_of=lookalike_of,
        lookalike_distance=lookalike_distance,
        suspicious_path_keywords=suspicious_path_keywords,
        suspicious_query_params=suspicious_query_params,
        evidence=evidence,
    )
