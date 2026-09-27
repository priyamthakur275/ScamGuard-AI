import email
import io
import ipaddress
import socket
import httpx
from fastapi import UploadFile

from app_service.core.config import get_settings
from ml_common.security.url_intelligence import analyze_url
from ml_common.security.email_forensics import analyze_email
from ml_common.security.voice_signals import analyze_voice_transcript

settings = get_settings()

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

MAX_EXTRACTED_LENGTH = 4000

# Max bytes read from any uploaded file (image/PDF/QR/email). Applies whether
# or not a reverse proxy is in front of this service -- self-hosted docker
# deployments cap request bodies at nginx, but Render/Vercel don't put
# anything in front of the app_service container, so without this an
# unbounded upload straight to the API is a memory-exhaustion vector during
# OCR/PDF parsing.
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB


class UnsafeUrlError(ValueError):
    """Raised when a user-supplied URL resolves to a non-public address.

    This is specifically for "this hostname resolves to something we
    should not fetch" -- an unresolvable/nonexistent hostname (a typo, a
    dead domain) is a different, much more mundane situation and must NOT
    be reported through this same path, or an ordinary broken link would
    get flagged as a blocked attack attempt.
    """


def _read_upload_bounded(file: UploadFile) -> bytes:
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(
            f"Uploaded file exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit."
        )
    return content


def _assert_public_host(hostname: str) -> list[str]:
    """Block requests to loopback/private/link-local/reserved addresses.

    Without this, a user could submit a URL like `http://169.254.169.254/...`
    (cloud metadata endpoint) or `http://localhost:5432` and have the
    *server* fetch it on their behalf -- classic SSRF. This is checked
    against every hostname the client actually connects to, including
    redirect targets (see the event hook below), not just the URL the user
    typed.

    Returns the resolved, validated-public IP addresses (as strings) so
    the caller can surface them as real "network intelligence" evidence
    rather than discarding them once the safety check passes.
    """
    if not hostname:
        raise UnsafeUrlError("URL has no hostname.")
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        # Could not resolve at all -- an ordinary broken/nonexistent
        # domain, not a blocked-attack situation. Let this propagate as a
        # plain, non-UnsafeUrlError failure so callers treat it as a
        # normal fetch failure, not a security block.
        raise ValueError(f"Could not resolve host: {hostname}") from exc

    resolved: list[str] = []
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise UnsafeUrlError(
                f"Refusing to fetch {hostname}: resolves to a non-public address ({ip_str})."
            )
        if ip_str not in resolved:
            resolved.append(ip_str)
    return resolved


def _validate_request_url(request: httpx.Request) -> None:
    if request.url.scheme not in ("http", "https"):
        raise UnsafeUrlError(f"Unsupported URL scheme: {request.url.scheme}")
    _assert_public_host(request.url.host)


def _get_tls_certificate_info(hostname: str, port: int = 443) -> dict | None:
    """Best-effort TLS certificate metadata (subject CN, issuer CN,
    expiry, and whether it's currently expired) via a short, separate TLS
    handshake. This is genuinely real data when it succeeds -- not
    fabricated -- but it is deliberately isolated from the main fetch:
    any failure (timeout, connection refused, non-TLS port, self-signed
    cert rejected) returns None rather than raising, so a certificate
    lookup can never break the primary URL analysis.

    HONESTY NOTE: this cannot be exercised against a real external HTTPS
    host in this project's automated test suite (the sandbox this was
    built in has no network access to arbitrary domains), so it is only
    unit-tested for its safe-failure behavior (unresolvable/blocked
    hosts), not for a live successful certificate fetch. Treat this as
    best-effort defense-in-depth information, not a verified-working
    feature end to end.
    """
    import ssl
    from datetime import datetime, timezone

    try:
        _assert_public_host(hostname)  # same SSRF guard, independent of the main fetch
        ctx = ssl.create_default_context()
        # Tightened from an earlier 4.0s: this connection is to a host we
        # JUST successfully connected to seconds ago (via the main fetch),
        # so a slow response here is unlikely to be legitimate -- capping
        # it shorter bounds the worst-case extra latency this adds to
        # every successful HTTPS scan without meaningfully increasing
        # false "unavailable" results for genuinely healthy hosts.
        with socket.create_connection((hostname, port), timeout=2.5) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as tls_sock:
                cert = tls_sock.getpeercert()
    except Exception:
        return None

    if not cert:
        return None

    def _name_field(name_tuples, field: str) -> str | None:
        for rdn in name_tuples or ():
            for key, value in rdn:
                if key == field:
                    return value
        return None

    not_after_str = cert.get("notAfter")
    is_expired = None
    not_after_iso = None
    if not_after_str:
        try:
            not_after = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            is_expired = datetime.now(timezone.utc) > not_after
            not_after_iso = not_after.isoformat()
        except ValueError:
            pass

    return {
        "subject_cn": _name_field(cert.get("subject"), "commonName"),
        "issuer_cn": _name_field(cert.get("issuer"), "commonName"),
        "not_after": not_after_iso,
        "is_expired": is_expired,
    }


def _fetch_url_safely(target_url: str, transport: httpx.BaseTransport | None = None) -> tuple[httpx.Response, list[str], list[dict]]:
    """Fetch a user-supplied URL with SSRF protection and real TLS
    verification. The host check runs as a request-level event hook so it
    also re-validates every redirect hop, not just the URL the user typed --
    otherwise an attacker-controlled 302 could still land the server on an
    internal address after the initial check passed.

    `transport` defaults to None (httpx's real network transport) and is
    only ever overridden in tests, with an `httpx.MockTransport`, to prove
    the redirect-hop validation actually fires mid-chain -- production
    behavior is completely unchanged by this parameter existing.

    Returns (response, resolved_ips_of_final_host, redirect_chain) where
    redirect_chain is the real sequence of hops actually followed
    (hostname + status code for each), taken from httpx's own response
    history -- not reconstructed or guessed.
    """
    # Validate before constructing a transport (including proxy setup).
    _validate_request_url(httpx.Request("GET", target_url))
    resolved_ips: list[str] = []

    def _capture_ips(request: httpx.Request) -> None:
        resolved_ips[:] = _assert_public_host(request.url.host)

    with httpx.Client(
        follow_redirects=True,
        max_redirects=5,
        timeout=12.0,
        headers={"User-Agent": DEFAULT_USER_AGENT},
        verify=True,
        event_hooks={"request": [_validate_request_url, _capture_ips]},
        transport=transport,
    ) as client:
        resp = client.get(target_url)
        resp.raise_for_status()

        redirect_chain = [
            {"url": str(hop.url), "status_code": hop.status_code}
            for hop in resp.history
        ]
        return resp, resolved_ips, redirect_chain


class ExtractionService:
    @staticmethod
    def extract(file: UploadFile | None, text: str | None, input_type: str) -> tuple[str, dict]:
        input_type = input_type.upper()

        if input_type == "URL":
            if not text or not text.strip():
                raise ValueError("URL address must be provided for URL input_type.")
            
            raw_url = text.strip()
            from urllib.parse import urlsplit
            candidate = urlsplit(raw_url if "://" in raw_url else "https://" + raw_url)
            if candidate.scheme not in {"http", "https"} or not candidate.hostname or any(c.isspace() for c in raw_url):
                raise ValueError("Enter a valid HTTP or HTTPS URL.")
            try:
                candidate.port
            except ValueError as exc:
                raise ValueError("URL port is invalid.") from exc
            # Normalize scheme if user entered without http/https
            target_url = raw_url
            if not target_url.startswith("http://") and not target_url.startswith("https://"):
                target_url = "https://" + target_url

            # Real, computed URL intelligence -- lexical/structural facts
            # about the URL string itself. This is OBSERVED EVIDENCE: it
            # does not depend on fetching the page and is not a model's
            # interpretation of anything, just facts about the URL text.
            intel = analyze_url(target_url)
            intel_lines = []
            if intel.is_punycode:
                intel_lines.append("- Hostname uses punycode/IDN encoding (possible homograph attack).")
            if intel.is_ip_literal:
                intel_lines.append("- Hostname is a raw IP address rather than a domain name.")
            if intel.is_suspicious_tld:
                intel_lines.append(f"- Top-level domain ({intel.registrable_domain.split('.')[-1]}) is one commonly abused in phishing campaigns.")
            if intel.is_shortened:
                intel_lines.append("- URL uses a link-shortening service, hiding the real destination.")
            if intel.has_userinfo_obfuscation:
                intel_lines.append("- URL contains userinfo (text before '@') that does not match the real destination host -- a known obfuscation trick.")
            if intel.lookalike_of:
                intel_lines.append(f"- Hostname closely resembles the brand domain '{intel.lookalike_of}' (edit distance {intel.lookalike_distance}) without being it -- possible brand impersonation.")
            if intel.subdomain_depth >= 3:
                intel_lines.append(f"- Unusually deep subdomain nesting ({intel.subdomain_depth} levels).")

            title = ""
            page_text = ""
            fetch_error = None
            resolved_ips: list[str] = []
            redirect_chain: list[dict] = []
            tls_info: dict | None = None

            try:
                resp, resolved_ips, redirect_chain = _fetch_url_safely(target_url)
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title = soup.title.string.strip() if soup.title and soup.title.string else ""
                    page_text = soup.get_text(separator=" ", strip=True)
                except Exception:
                    page_text = resp.text[:2000]
                redirect_count = len(resp.history)
                if intel.scheme == "https":
                    # Best-effort, isolated -- see _get_tls_certificate_info's
                    # docstring for why this can never break the main fetch
                    # and why it isn't claimed to be verified end-to-end.
                    tls_info = _get_tls_certificate_info(intel.hostname, intel.port or 443)
            except UnsafeUrlError as exc:
                # Do not silently fall through to "analyze the URL text
                # itself" for this case -- a blocked SSRF attempt should be
                # visible as such, not disguised as an ordinary fetch failure.
                fetch_error = str(exc)
                metadata = {
                    "url": target_url,
                    "fetch_status": "blocked_unsafe_target",
                    "url_intelligence": intel.to_dict(),
                }
                evidence_block = ("\nObserved URL signals:\n" + "\n".join(intel_lines)) if intel_lines else ""
                return (f"URL Target (fetch blocked): {target_url}\nReason: {fetch_error}{evidence_block}")[:MAX_EXTRACTED_LENGTH], metadata
            except Exception as exc:
                # If network fetch fails (redirect loop, auth wall, bot block, DNS fail),
                # do NOT crash! Fall back to analyzing the URL itself as the target payload.
                fetch_error = str(exc)
                redirect_count = 0

            evidence_block = ("\nObserved URL signals:\n" + "\n".join(intel_lines)) if intel_lines else ""

            if page_text:
                extracted = f"URL: {target_url}\nTitle: {title}\nContent:\n{page_text}{evidence_block}"
            else:
                extracted = f"URL Target: {target_url}{evidence_block}"

            metadata = {
                "url": target_url,
                "title": title or "External Domain Target",
                "url_intelligence": {
                    **intel.to_dict(),
                    "redirect_count": redirect_count,
                    "redirect_chain": redirect_chain,
                    "resolved_ips": resolved_ips,
                    "tls": tls_info,
                },
            }
            if fetch_error:
                metadata["fetch_status"] = "direct_url_analysis"

            return extracted[:MAX_EXTRACTED_LENGTH].strip(), metadata

        elif input_type == "EMAIL":
            try:
                if file:
                    content = _read_upload_bounded(file)
                    if isinstance(content, bytes):
                        msg = email.message_from_bytes(content)
                    else:
                        msg = email.message_from_string(content)
                elif text:
                    msg = email.message_from_string(text)
                else:
                    raise ValueError("File or text must be provided for EMAIL input_type.")

                subject = msg.get("Subject", "")
                sender = msg.get("From", "")

                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body += part.get_payload(decode=True).decode(
                                part.get_content_charset() or "utf-8", errors="ignore"
                            )
                        elif part.get_content_type() == "text/html" and not body:
                            html = part.get_payload(decode=True).decode(
                                part.get_content_charset() or "utf-8", errors="ignore"
                            )
                            try:
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(html, "html.parser")
                                body = soup.get_text(separator=" ", strip=True)
                            except Exception:
                                body = html
                else:
                    body = msg.get_payload(decode=True).decode(
                        msg.get_content_charset() or "utf-8", errors="ignore"
                    )

                if not (body.strip() or subject.strip()):
                    raise ValueError("Email contains no subject or readable message body.")

                extracted_text = f"Subject: {subject}\nSender: {sender}\n\n{body}"
                if not extracted_text.strip():
                    extracted_text = f"Email communication from {sender or 'unknown sender'} with subject {subject or 'No subject'}"

                # Real header forensics + content signal detection -- see
                # email_forensics.py. Never fabricates SPF/DKIM/DMARC.
                forensics = analyze_email(msg, body)
                evidence_lines = [
                    f"- {s.reason}"
                    for s in (*forensics.header_evidence, *forensics.content_evidence, *forensics.attachment_evidence)
                ]
                if evidence_lines:
                    extracted_text += "\n\nObserved email signals:\n" + "\n".join(evidence_lines)

                metadata = {
                    "subject": subject,
                    "from": sender,
                    "email_forensics": forensics.to_dict(),
                }
                return extracted_text[:MAX_EXTRACTED_LENGTH].strip(), metadata
            except Exception as e:
                raise ValueError(f"Failed to process EMAIL: {str(e)}")

        elif input_type == "QR":
            if not file:
                raise ValueError("Image file must be provided for QR input_type.")
            try:
                from PIL import Image
                from pyzbar.pyzbar import decode

                img = Image.open(io.BytesIO(_read_upload_bounded(file)))
                decoded_objects = decode(img)
                if not decoded_objects:
                    raise ValueError("No QR code or barcode pattern found in the uploaded image.")

                obj = decoded_objects[0]
                data = obj.data.decode("utf-8", errors="ignore")
                return data[:MAX_EXTRACTED_LENGTH].strip(), {"qr_type": str(obj.type)}
            except Exception as e:
                raise ValueError(f"Failed to scan QR code: {str(e)}")

        elif input_type == "IMAGE":
            if not file:
                raise ValueError("Image file must be provided for IMAGE input_type.")
            content = _read_upload_bounded(file)
            try:
                from PIL import Image
                import pytesseract

                if getattr(settings, "TESSERACT_CMD", None):
                    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

                img = Image.open(io.BytesIO(content))
                extracted_text = pytesseract.image_to_string(img, timeout=20)
                if not extracted_text or not extracted_text.strip():
                    raise ValueError("No readable text was found in this image. Use a clearer image or the QR tab for QR codes.")
                return extracted_text[:MAX_EXTRACTED_LENGTH].strip(), {"ocr_detected": True}
            except Exception as e:
                if "tesseract" in str(e).lower() or "not installed" in str(e).lower():
                    raise ValueError("OCR is unavailable. Install Tesseract on the server or paste the image text for analysis.") from e
                raise ValueError("Image text extraction failed. Use a clear, supported image with readable text.") from e

        elif input_type == "PDF":
            if not file:
                raise ValueError("PDF document must be provided for PDF input_type.")
            try:
                from pypdf import PdfReader

                reader = PdfReader(io.BytesIO(_read_upload_bounded(file)))
                extracted_text = ""
                # Scan up to the first 25 pages
                pages_to_scan = reader.pages[:25]
                for page in pages_to_scan:
                    try:
                        p_text = page.extract_text()
                        if p_text:
                            extracted_text += p_text + "\n"
                    except Exception:
                        continue

                extracted_text = extracted_text.strip()
                if not extracted_text:
                    raise ValueError("This PDF has no extractable text. Upload a page image for OCR or paste the document text.")

                return extracted_text[:MAX_EXTRACTED_LENGTH].strip(), {"pages": len(reader.pages)}
            except Exception as e:
                raise ValueError(f"Failed to parse PDF document: {str(e)}")

        elif input_type == "VOICE":
            # Two paths, per the honesty requirement:
            # 1. `text` is provided -- this is a REAL transcript already
            #    produced by the browser's own Web Speech API (client-side,
            #    live, no server transcription involved at all).
            # 2. `file` is provided (a recorded/uploaded audio file) --
            #    attempt server-side transcription via a configured
            #    provider. If none is configured, this fails honestly
            #    (TranscriptionUnavailableError -> ValueError -> clean 422),
            #    never with a fabricated transcript.
            if text and text.strip():
                transcript = text.strip()
            elif file:
                from app_service.services.voice_transcription import transcribe_audio, TranscriptionUnavailableError
                audio_bytes = _read_upload_bounded(file)
                try:
                    transcript = transcribe_audio(audio_bytes, file.content_type or "audio/wav")
                except TranscriptionUnavailableError as exc:
                    raise ValueError(str(exc))
            else:
                raise ValueError("Either a transcript or an audio file must be provided for VOICE input_type.")

            if not transcript.strip():
                raise ValueError("Transcription produced no text to analyze.")

            voice_signals = analyze_voice_transcript(transcript)
            evidence_lines = [f"- {s.reason}" for s in voice_signals]
            extracted_text = transcript
            if evidence_lines:
                extracted_text += "\n\nObserved voice-call signals:\n" + "\n".join(evidence_lines)

            metadata = {
                "transcript": transcript,
                "voice_evidence": [
                    {"code": s.code, "severity": s.severity, "reason": s.reason} for s in voice_signals
                ],
            }
            return extracted_text[:MAX_EXTRACTED_LENGTH].strip(), metadata

        elif input_type == "TEXT":
            text = text or ""
            return text[:MAX_EXTRACTED_LENGTH].strip(), {}

        else:
            raise ValueError(f"Unsupported input channel: {input_type}")
