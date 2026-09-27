"""Email header forensics and content signal detection.

Design principles (same as url_intelligence.py, which this module reuses
for sender-domain and embedded-link analysis):

1. NEVER fabricate SPF/DKIM/DMARC. This module does not perform live SPF/
   DKIM/DMARC verification itself (that requires DNS TXT lookups against
   the sending domain, cryptographic signature verification, and policy
   fetching -- a real, separate subsystem this module does not build).
   It only PARSES what the receiving mail server already recorded in the
   email's own `Authentication-Results` header, if present. When that
   header is missing, or doesn't mention one of the three mechanisms,
   the result is the literal string "not_available" -- never a guessed
   or defaulted pass/fail.
2. Every signal is an independent EvidenceSignal (code/severity/reason),
   never an aggregate verdict. A missing Reply-To is not evidence of
   anything; a Reply-To/From domain MISMATCH is.
3. Nothing here performs a network request. Embedded URLs are handed to
   ml_common.security.url_intelligence.analyze_url() (pure, no network)
   for their own evidence; the SSRF-guarded live fetch (extraction.py)
   is a separate, existing concern this module does not duplicate.
"""
import ipaddress
import re
from dataclasses import dataclass
from email.message import Message
from email.utils import parseaddr

from ml_common.security.url_intelligence import EvidenceSignal, analyze_url

_URL_PATTERN = re.compile(r"https?://[^\s<>\"')]+")
_IPV4_PATTERN = re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b")

_DANGEROUS_ATTACHMENT_EXTENSIONS = frozenset({
    ".exe", ".scr", ".bat", ".cmd", ".com", ".pif", ".js", ".jse", ".vbs",
    ".vbe", ".jar", ".ps1", ".msi", ".msp", ".hta", ".wsf", ".lnk",
})

_URGENCY_KEYWORDS = frozenset({
    "urgent", "immediately", "expire", "expires", "expiring", "act now",
    "final notice", "last chance", "deadline", "within 24 hours",
    "account will be suspended", "account will be closed",
})
_PAYMENT_REQUEST_KEYWORDS = frozenset({
    "wire transfer", "gift card", "payment required", "invoice attached",
    "bank details", "routing number", "account number", "pay now",
    "outstanding balance", "overdue payment",
})
_CREDENTIAL_REQUEST_KEYWORDS = frozenset({
    "verify your password", "confirm your password", "login to verify",
    "update your credentials", "re-enter your password", "click to sign in",
    "verify your identity", "confirm your account",
})
_OTP_REQUEST_KEYWORDS = frozenset({
    "otp", "one-time password", "one time password", "verification code",
    "security code", "pin code", "share the code",
})
_THREAT_KEYWORDS = frozenset({
    "legal action", "account suspended", "account terminated", "police",
    "law enforcement", "court order", "lawsuit", "penalty", "arrest",
})
_SUSPICIOUS_INSTRUCTION_KEYWORDS = frozenset({
    "do not tell anyone", "keep this confidential", "don't inform your bank",
    "do not contact", "reply directly to this email only",
})

_KEYWORD_CATEGORIES: tuple[tuple[str, frozenset, str], ...] = (
    ("urgency_language", _URGENCY_KEYWORDS, "low"),
    ("payment_request", _PAYMENT_REQUEST_KEYWORDS, "medium"),
    ("credential_request", _CREDENTIAL_REQUEST_KEYWORDS, "high"),
    ("otp_request", _OTP_REQUEST_KEYWORDS, "high"),
    ("threat_language", _THREAT_KEYWORDS, "medium"),
    ("suspicious_instructions", _SUSPICIOUS_INSTRUCTION_KEYWORDS, "high"),
)


def _domain_of(address: str | None) -> str | None:
    if not address:
        return None
    _, email_addr = parseaddr(address)
    if "@" not in email_addr:
        return None
    return email_addr.rsplit("@", 1)[1].lower().strip() or None


@dataclass(frozen=True)
class EmailHeaderInfo:
    from_address: str | None
    from_domain: str | None
    to_address: str | None
    reply_to: str | None
    reply_to_domain: str | None
    return_path: str | None
    return_path_domain: str | None
    subject: str | None
    date: str | None
    message_id: str | None
    received_chain: tuple[str, ...]
    spf: str  # a real parsed value, or the literal "not_available"
    dkim: str
    dmarc: str
    authentication_results_raw: str | None

    def to_dict(self) -> dict:
        return {
            "from_address": self.from_address,
            "from_domain": self.from_domain,
            "to_address": self.to_address,
            "reply_to": self.reply_to,
            "reply_to_domain": self.reply_to_domain,
            "return_path": self.return_path,
            "return_path_domain": self.return_path_domain,
            "subject": self.subject,
            "date": self.date,
            "message_id": self.message_id,
            "received_chain": list(self.received_chain),
            "spf": self.spf,
            "dkim": self.dkim,
            "dmarc": self.dmarc,
            "authentication_results_raw": self.authentication_results_raw,
        }


@dataclass(frozen=True)
class AttachmentInfo:
    filename: str | None
    content_type: str | None
    size_bytes: int

    def to_dict(self) -> dict:
        return {"filename": self.filename, "content_type": self.content_type, "size_bytes": self.size_bytes}


@dataclass(frozen=True)
class EmailForensicsResult:
    headers: EmailHeaderInfo
    header_evidence: tuple[EvidenceSignal, ...]
    content_evidence: tuple[EvidenceSignal, ...]
    url_evidence: dict  # {url: UrlIntelligence.to_dict()} for each embedded link
    attachments: tuple[AttachmentInfo, ...]
    attachment_evidence: tuple[EvidenceSignal, ...]

    def to_dict(self) -> dict:
        return {
            "headers": self.headers.to_dict(),
            "header_evidence": [_sig_dict(s) for s in self.header_evidence],
            "content_evidence": [_sig_dict(s) for s in self.content_evidence],
            "url_evidence": self.url_evidence,
            "attachments": [a.to_dict() for a in self.attachments],
            "attachment_evidence": [_sig_dict(s) for s in self.attachment_evidence],
        }


def _sig_dict(signal: EvidenceSignal) -> dict:
    return {"code": signal.code, "severity": signal.severity, "reason": signal.reason}


def _parse_auth_results(raw: str | None) -> tuple[str, str, str]:
    """Parses spf=/dkim=/dmarc= tokens out of a real Authentication-Results
    header value. Returns "not_available" for any mechanism not present in
    the header (including when the header itself is entirely missing).
    This is exactly and only what the receiving mail server itself
    recorded -- never independently verified or guessed here.
    """
    if not raw:
        return "not_available", "not_available", "not_available"

    def _extract(mechanism: str) -> str:
        match = re.search(rf"\b{mechanism}=(\w+)", raw, re.IGNORECASE)
        return match.group(1).lower() if match else "not_available"

    return _extract("spf"), _extract("dkim"), _extract("dmarc")


def _extract_headers(msg: Message) -> EmailHeaderInfo:
    from_addr = msg.get("From")
    reply_to = msg.get("Reply-To")
    return_path = msg.get("Return-Path")
    auth_results = msg.get("Authentication-Results")

    spf, dkim, dmarc = _parse_auth_results(auth_results)

    received_chain = tuple(msg.get_all("Received", []))

    return EmailHeaderInfo(
        from_address=from_addr,
        from_domain=_domain_of(from_addr),
        to_address=msg.get("To"),
        reply_to=reply_to,
        reply_to_domain=_domain_of(reply_to),
        return_path=return_path,
        return_path_domain=_domain_of(return_path),
        subject=msg.get("Subject"),
        date=msg.get("Date"),
        message_id=msg.get("Message-ID"),
        received_chain=received_chain,
        spf=spf,
        dkim=dkim,
        dmarc=dmarc,
        authentication_results_raw=auth_results,
    )


def _analyze_received_chain(headers: EmailHeaderInfo) -> tuple[EvidenceSignal, ...]:
    """Real, deterministic facts extracted from the Received header
    chain -- deliberately conservative. Received header formats vary
    enormously across mail providers and relays, so this does NOT attempt
    to parse sender hostnames out of them (too unreliable, high false-
    positive risk) -- it only checks two things that are genuinely safe
    to state as fact: whether a chain exists at all, and whether any hop
    embeds a private/loopback/reserved IP literal in its own text. Both
    are informational (low severity) -- neither implies maliciousness by
    itself; both are common for entirely legitimate reasons (pasted
    headers, internal corporate relays).
    """
    signals: list[EvidenceSignal] = []

    if not headers.received_chain and (headers.from_address or headers.authentication_results_raw):
        signals.append(EvidenceSignal(
            "no_received_chain", "low",
            "No Received headers are present in this header set, so the actual "
            "delivery path could not be examined. Common for manually pasted "
            "headers or partial forwards -- not itself evidence of anything.",
        ))
        return tuple(signals)

    private_ip_hops = 0
    for hop in headers.received_chain:
        for ip_str in _IPV4_PATTERN.findall(hop):
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                continue
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                private_ip_hops += 1
                break  # one match per hop is enough to count it

    if private_ip_hops:
        signals.append(EvidenceSignal(
            "received_chain_private_ip", "low",
            f"{private_ip_hops} hop(s) in the Received chain reference a private/"
            "internal IP address. This is routine for mail relayed through "
            "internal corporate infrastructure and is not itself suspicious.",
        ))

    return tuple(signals)


def _build_header_evidence(headers: EmailHeaderInfo) -> tuple[EvidenceSignal, ...]:
    signals: list[EvidenceSignal] = []

    if headers.spf == "fail":
        signals.append(EvidenceSignal(
            "spf_fail", "high",
            "The receiving mail server recorded an SPF FAIL for this message -- the "
            "sending server was not authorized to send mail for this domain.",
        ))
    if headers.dkim == "fail":
        signals.append(EvidenceSignal(
            "dkim_fail", "high",
            "The receiving mail server recorded a DKIM FAIL -- the message's digital "
            "signature did not verify, meaning it may have been altered or spoofed.",
        ))
    if headers.dmarc == "fail":
        signals.append(EvidenceSignal(
            "dmarc_fail", "high",
            "The receiving mail server recorded a DMARC FAIL -- this message did not "
            "meet the sending domain's own published authentication policy.",
        ))
    if headers.spf == "not_available" and headers.dkim == "not_available" and headers.dmarc == "not_available":
        signals.append(EvidenceSignal(
            "no_authentication_results", "low",
            "This email (or pasted header set) has no Authentication-Results header "
            "at all, so SPF/DKIM/DMARC status could not be read. This is common for "
            "manually pasted headers or forwarded mail, and is not itself evidence "
            "of anything suspicious.",
        ))

    if headers.reply_to_domain and headers.from_domain and headers.reply_to_domain != headers.from_domain:
        signals.append(EvidenceSignal(
            "reply_to_domain_mismatch", "medium",
            f"The Reply-To domain ('{headers.reply_to_domain}') does not match the "
            f"From domain ('{headers.from_domain}') -- replies would go somewhere "
            "other than the apparent sender, a common phishing pattern.",
        ))
    if headers.return_path_domain and headers.from_domain and headers.return_path_domain != headers.from_domain:
        signals.append(EvidenceSignal(
            "return_path_domain_mismatch", "medium",
            f"The Return-Path domain ('{headers.return_path_domain}') does not match "
            f"the From domain ('{headers.from_domain}') -- bounces would go somewhere "
            "other than the apparent sender.",
        ))

    if headers.from_domain:
        # Reuse the exact same lookalike/punycode/suspicious-TLD logic used
        # for URLs, against the sender's own domain -- a domain is a domain.
        sender_intel = analyze_url(f"http://{headers.from_domain}/")
        if sender_intel.lookalike_of:
            signals.append(EvidenceSignal(
                "sender_domain_lookalike", "high",
                f"The sender domain ('{headers.from_domain}') closely resembles the "
                f"known brand domain '{sender_intel.lookalike_of}' "
                f"(edit distance {sender_intel.lookalike_distance}) without being it.",
            ))
        if sender_intel.is_punycode:
            signals.append(EvidenceSignal(
                "sender_domain_punycode", "medium",
                f"The sender domain ('{headers.from_domain}') uses punycode/IDN "
                "encoding, which can visually spoof a legitimate brand name.",
            ))
        if sender_intel.is_suspicious_tld:
            signals.append(EvidenceSignal(
                "sender_domain_suspicious_tld", "low",
                f"The sender domain's TLD is one commonly abused in phishing "
                "campaigns. Many legitimate senders use it too.",
            ))

    signals.extend(_analyze_received_chain(headers))

    return tuple(signals)


def _build_content_evidence(body_text: str) -> tuple[EvidenceSignal, ...]:
    text_lower = body_text.lower()
    signals: list[EvidenceSignal] = []
    for code, keywords, severity in _KEYWORD_CATEGORIES:
        matched = sorted(kw for kw in keywords if kw in text_lower)
        if matched:
            signals.append(EvidenceSignal(
                code, severity,
                f"Message body contains language commonly seen in {code.replace('_', ' ')} "
                f"attempts: {', '.join(matched[:3])}{'...' if len(matched) > 3 else ''}.",
            ))
    return tuple(signals)


def _build_attachment_evidence(attachments: tuple[AttachmentInfo, ...]) -> tuple[EvidenceSignal, ...]:
    signals: list[EvidenceSignal] = []
    for att in attachments:
        if not att.filename:
            continue
        name_lower = att.filename.lower()
        for ext in _DANGEROUS_ATTACHMENT_EXTENSIONS:
            if name_lower.endswith(ext):
                signals.append(EvidenceSignal(
                    "dangerous_attachment_extension", "high",
                    f"Attachment '{att.filename}' has an executable/script extension "
                    f"({ext}) -- a common malware-delivery pattern.",
                ))
                break
        # Double-extension trick: "invoice.pdf.exe"
        name_parts = att.filename.split(".")
        if len(name_parts) > 2 and f".{name_parts[-1].lower()}" in _DANGEROUS_ATTACHMENT_EXTENSIONS:
            signals.append(EvidenceSignal(
                "double_extension_attachment", "high",
                f"Attachment '{att.filename}' uses a double-extension pattern often "
                "used to disguise an executable as a document.",
            ))
    return tuple(signals)


def analyze_email(msg: Message, body_text: str) -> EmailForensicsResult:
    """msg is an already-parsed email.message.Message (email.message_from_*
    output); body_text is the plain-text body already extracted by the
    caller (extraction.py already does MIME-part walking/decoding).
    """
    headers = _extract_headers(msg)
    header_evidence = _build_header_evidence(headers)
    content_evidence = _build_content_evidence(body_text)

    urls_found = list(dict.fromkeys(_URL_PATTERN.findall(body_text)))[:10]  # dedupe, cap
    url_evidence = {url: analyze_url(url).to_dict() for url in urls_found}

    attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            filename = part.get_filename()
            if filename:
                payload = part.get_payload(decode=True)
                attachments.append(AttachmentInfo(
                    filename=filename,
                    content_type=part.get_content_type(),
                    size_bytes=len(payload) if payload else 0,
                ))
    attachment_evidence = _build_attachment_evidence(tuple(attachments))

    return EmailForensicsResult(
        headers=headers,
        header_evidence=header_evidence,
        content_evidence=content_evidence,
        url_evidence=url_evidence,
        attachments=tuple(attachments),
        attachment_evidence=attachment_evidence,
    )
