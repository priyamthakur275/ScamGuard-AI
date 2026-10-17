"""Safety tools: UPI payment checks (QR codes and pay-safe), attachment checks
and the "what makes it a scam" counterfactual. Everything here is rule based
and explainable; nothing is stored."""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from dataclasses import asdict, dataclass, field
from urllib.parse import parse_qs, unquote, urlparse


@dataclass
class Flag:
    level: str  # "danger" | "warning" | "info" | "ok"
    title: str
    detail: str


@dataclass
class ToolResult:
    risk: str  # "high" | "medium" | "low"
    summary: str
    flags: list[Flag] = field(default_factory=list)
    facts: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _risk(flags: list[Flag]) -> str:
    if any(f.level == "danger" for f in flags):
        return "high"
    if any(f.level == "warning" for f in flags):
        return "medium"
    return "low"


# ---------------------------------------------------------------- UPI
_VPA = re.compile(r"^[a-z0-9._-]{2,256}@[a-z][a-z0-9.-]{1,63}$", re.I)
_BAIT_WORDS = re.compile(
    r"refund|cash\s?back|reward|prize|lottery|lucky|gift|winner|kyc|verify|verification|support|helpdesk|"
    r"customer\s?care|care|claim|bonus|offer|receive|credit|unlock|activation|fine|penalty|customs|courier",
    re.I,
)
_RECEIVE = re.compile(r"\b(receive|get|claim|credit(ed)?|refund|cash\s?back|prize|reward|payment\s+to\s+you)\b", re.I)

# Why someone asked you to pay -> what it usually means.
REASONS: dict[str, tuple[str, str, str]] = {
    "shop": ("ok", "Paying a shop or person you know", "Normal. Check the payee name shown in your UPI app before entering the PIN."),
    "bill": ("ok", "Paying a bill from the official app or website", "Normal when you started it yourself from the official app."),
    "receive": ("danger", "To RECEIVE money (refund, prize, buyer paying you)",
                "This is always a scam. You never scan a QR code, accept a collect request or enter your UPI PIN to receive money. The PIN only ever sends money out."),
    "kyc": ("danger", "KYC, account unblock or verification fee",
            "Banks and wallets do not take a UPI payment to update KYC or unblock an account. This is a scam."),
    "job": ("danger", "Job registration, task or training fee",
            "Real employers do not charge to hire you, and 'pay to unlock task earnings' is a known task scam."),
    "customs": ("danger", "Parcel, customs or courier release fee",
                "Customs duty is not collected over UPI by phone or WhatsApp. This is a known parcel scam."),
    "police": ("danger", "Police, CBI, court or 'digital arrest' fine",
               "Police and courts never collect fines over UPI on a call, and 'digital arrest' does not exist. Hang up and call 1930."),
    "investment": ("warning", "Investment, trading or crypto tip",
                   "Guaranteed or very high returns are the hallmark of investment fraud. Use only SEBI-registered brokers' own apps."),
    "relative": ("warning", "A friend or relative asking urgently by message",
                 "Accounts get hacked and voices get cloned. Call the person on the number you already have before paying."),
    "electricity": ("danger", "Electricity disconnection 'tonight'",
                    "Power companies do not disconnect over a WhatsApp message or collect dues to a personal UPI ID."),
    "other": ("info", "Something else", "Pay only people you can verify, and only when you started the payment."),
}


def _name_tokens(name: str) -> set[str]:
    return {t for t in re.findall(r"[a-z]+", name.lower()) if len(t) > 1}


def analyze_upi(vpa: str = "", payee_name: str = "", amount: str = "", note: str = "",
                reason: str = "", expected_name: str = "", source: str = "manual") -> ToolResult:
    flags: list[Flag] = []
    vpa = vpa.strip()
    if vpa:
        if not _VPA.match(vpa):
            flags.append(Flag("warning", "Unusual UPI ID", f"'{vpa}' does not look like a normal UPI ID (name@bank)."))
        local = vpa.split("@")[0]
        bait = _BAIT_WORDS.search(local)
        if bait:
            flags.append(Flag("danger", "Bait word in the UPI ID",
                              f"The UPI ID contains '{bait.group(0)}'. Scammers name their IDs like refunds, rewards or support desks so the payment looks official."))
        if re.fullmatch(r"[6-9]\d{9}", re.sub(r"\D", "", local) or "x") and payee_name and _BAIT_WORDS.search(payee_name):
            flags.append(Flag("warning", "Phone-number UPI ID with an official-sounding name",
                              "A personal phone-number UPI ID that calls itself a company or helpdesk is a common trick."))
    if payee_name and _BAIT_WORDS.search(payee_name):
        flags.append(Flag("warning", "Official-sounding payee name",
                          f"The payee calls itself '{payee_name}'. Anyone can set any display name; check the name your bank shows before paying."))
    if expected_name and payee_name:
        a, b = _name_tokens(expected_name), _name_tokens(payee_name)
        if a and b and not (a & b):
            flags.append(Flag("danger", "Payee name does not match",
                              f"You expected '{expected_name}' but the payment goes to '{payee_name}'. Do not pay."))
    if note and _BAIT_WORDS.search(note):
        flags.append(Flag("warning", "Suspicious payment note", f"The note says '{note}'."))
    if note and _RECEIVE.search(note) and source == "qr":
        flags.append(Flag("danger", "QR code says you will receive money",
                          "Scanning a QR code only ever sends money. A QR 'to receive' a refund, prize or buyer's payment is a scam."))
    try:
        amt = float(amount) if amount else None
    except ValueError:
        amt = None
    if amt is not None and source == "qr":
        flags.append(Flag("info", "Amount is pre-filled", f"This QR code fills in ₹{amt:,.2f} for you. Make sure you meant to pay exactly that."))
    if amt is not None and amt >= 100000:
        flags.append(Flag("warning", "Large amount", "For large payments, verify the receiver by phone or in person first."))
    if reason:
        level, title, detail = REASONS.get(reason, REASONS["other"])
        if level in ("danger", "warning"):
            flags.append(Flag(level, title, detail))
        elif level == "ok" and not flags:
            flags.append(Flag("ok", title, detail))

    risk = _risk(flags)
    summary = {
        "high": "Do not pay. This matches a known UPI scam pattern.",
        "medium": "Be careful. Verify the receiver before you enter your PIN.",
        "low": "No scam signs found. Still check the payee name your UPI app shows before entering the PIN.",
    }[risk]
    facts = {k: v for k, v in {"upi_id": vpa, "payee_name": payee_name, "amount": amount, "note": note}.items() if v}
    return ToolResult(risk, summary, flags, facts)


def parse_upi_uri(data: str) -> dict | None:
    """Parse upi://pay?pa=..&pn=..&am=..&tn=.. (the format inside UPI QR codes)."""
    s = data.strip()
    if not s.lower().startswith("upi://"):
        return None
    q = {k.lower(): unquote(v[0]) for k, v in parse_qs(urlparse(s).query).items() if v}
    return {"vpa": q.get("pa", ""), "payee_name": q.get("pn", ""), "amount": q.get("am", ""),
            "note": q.get("tn", "") or q.get("tr", ""), "mode": urlparse(s).netloc.lower()}


# ---------------------------------------------------------------- attachments
MAX_FILE_BYTES = 10 * 1024 * 1024
_DANGEROUS_EXT = {"apk", "xapk", "apks", "exe", "msi", "scr", "bat", "cmd", "com", "pif", "js", "jse", "vbs", "vbe",
                  "wsf", "hta", "lnk", "ps1", "jar", "iso", "img", "dll", "reg", "msix", "appx", "dmg", "pkg", "sh"}
_ARCHIVE_EXT = {"zip", "rar", "7z", "tar", "gz"}
_MACRO_EXT = {"docm", "xlsm", "pptm", "dotm", "xltm"}
_DOC_LIKE = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "jpg", "jpeg", "png", "gif", "webp", "txt", "mp4", "mp3"}


def _sniff(head: bytes, data: bytes) -> tuple[str, list[str]]:
    """Real file type from its first bytes (not from its name)."""
    notes: list[str] = []
    if head.startswith(b"MZ"):
        return "windows-program", notes
    if head.startswith(b"\x7fELF"):
        return "linux-program", notes
    if head.startswith(b"%PDF"):
        for marker, label in ((b"/JavaScript", "JavaScript"), (b"/Launch", "a Launch action"), (b"/OpenAction", "an auto-open action"),
                              (b"/EmbeddedFile", "an embedded file")):
            if marker in data:
                notes.append(label)
        return "pdf", notes
    if head.startswith(b"\xd0\xcf\x11\xe0"):
        if b"VBA" in data or b"Macros" in data:
            notes.append("macros")
        return "office-legacy", notes
    if head.startswith(b"PK\x03\x04"):
        try:
            names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        except zipfile.BadZipFile:
            return "zip", notes
        low = [n.lower() for n in names]
        if "androidmanifest.xml" in low or "classes.dex" in low:
            return "android-app", notes
        if any(n.endswith("vbaproject.bin") for n in low):
            notes.append("macros")
        if "[content_types].xml" in low:
            return "office", notes
        inner = [n for n in low if n.rsplit(".", 1)[-1] in _DANGEROUS_EXT]
        if inner:
            notes.append("programs inside: " + ", ".join(inner[:3]))
        return "zip", notes
    for sig, kind in ((b"\x89PNG", "image"), (b"\xff\xd8\xff", "image"), (b"GIF8", "image"), (b"RIFF", "media"),
                      (b"Rar!", "archive"), (b"7z\xbc\xaf", "archive"), (b"\x1f\x8b", "archive")):
        if head.startswith(sig):
            return kind, notes
    if head[4:8] == b"ftyp":
        return "media", notes
    if all(32 <= c < 127 or c in (9, 10, 13) for c in head[:512]):
        text = data[:4096].decode("ascii", "ignore").lower()
        if any(k in text for k in ("wscript", "powershell", "<script", "cmd.exe", "eval(", "#!/bin/")):
            return "script", notes
        return "text", notes
    return "unknown", notes


def check_file(filename: str, data: bytes) -> ToolResult:
    name = (filename or "file").strip()
    parts = name.lower().split(".")
    ext = parts[-1] if len(parts) > 1 else ""
    kind, notes = _sniff(data[:16], data)
    flags: list[Flag] = []

    if kind == "android-app" or ext in {"apk", "xapk", "apks"}:
        flags.append(Flag("danger", "This is an Android app (APK)",
                          "Fake 'bank rewards', 'KYC update', 'electricity bill' and 'wedding invitation' APKs sent on WhatsApp steal OTPs and empty accounts. "
                          "Never install apps from a message; banks only use the Play Store."))
    elif kind in ("windows-program", "linux-program") or ext in _DANGEROUS_EXT:
        flags.append(Flag("danger", "This file is a program, not a document",
                          f"Opening a .{ext or kind} file runs code on your device. Do not open it unless you were expecting exactly this program."))
    elif kind == "script":
        flags.append(Flag("danger", "This file contains a script", "It can run commands when opened. Do not open it."))
    if len(parts) > 2 and parts[-2] in _DOC_LIKE and (ext in _DANGEROUS_EXT or kind in ("android-app", "windows-program")):
        flags.append(Flag("danger", "Double extension trick", f"'{name}' pretends to be a .{parts[-2]} but is really a .{ext}."))
    claimed_doc = ext in _DOC_LIKE
    if claimed_doc and kind in ("android-app", "windows-program", "linux-program", "script"):
        flags.append(Flag("danger", "The name lies about the file type",
                          f"It is named .{ext} but the contents are a {kind.replace('-', ' ')}."))
    if "macros" in notes or ext in _MACRO_EXT:
        flags.append(Flag("danger", "Document with macros", "Macros can install malware. If Office asks to 'Enable content', do not."))
    pdf_bits = [n for n in notes if n in ("JavaScript", "a Launch action", "an auto-open action", "an embedded file")]
    if pdf_bits:
        flags.append(Flag("warning", "PDF with active content", "This PDF contains " + ", ".join(pdf_bits) + ". Normal bills and letters do not need this."))
    if any(n.startswith("programs inside") for n in notes):
        flags.append(Flag("danger", "Archive hides a program", next(n for n in notes if n.startswith("programs inside")) + "."))
    elif ext in _ARCHIVE_EXT or kind in ("zip", "archive"):
        flags.append(Flag("warning", "Compressed archive", "Archives are used to sneak programs past checks. Look inside before opening anything."))
    if not flags:
        flags.append(Flag("ok", "No dangerous file type found",
                          "The contents match an ordinary file type. A safe file can still carry a scam message, so check what it asks you to do."))

    sha = hashlib.sha256(data).hexdigest()
    risk = _risk(flags)
    summary = {"high": "Do not open or install this file.", "medium": "Be careful with this file.",
               "low": "This looks like an ordinary file."}[risk]
    facts = {"file_name": name, "size_bytes": len(data), "detected_type": kind, "sha256": sha,
             "virustotal_url": f"https://www.virustotal.com/gui/file/{sha}"}
    return ToolResult(risk, summary, flags, facts)


# ---------------------------------------------------------------- what-if
_INTENT_LABELS = {
    "asks_for_secret": "asking for your OTP / PIN / password",
}


def _score(text: str) -> float:
    from app_service.services.message_service import get_in_process_prediction_service
    from ml_service.services.prediction_service import PredictionRequest

    return float(get_in_process_prediction_service().predict(PredictionRequest(text=text, input_type="TEXT", metadata=None)).threat_score)


_LINK = re.compile(r"(https?://\S+|www\.\S+|\b[a-z0-9-]+(\.[a-z0-9-]+)*\.(xyz|top|in|com|co|net|org|info|online|site|link|app|live|shop|click)\b\S*)", re.I)
_CONTACT = re.compile(r"(\+?91[\s-]?)?\b[6-9]\d{9}\b|\b[\w.-]+@(ok\w+|ybl|paytm|upi|ibl|axl)\b", re.I)


def what_if(text: str, max_parts: int = 8) -> dict:
    """Remove each suspicious part in turn and re-score, showing how much each
    one is responsible for the risk."""
    from ml_service.inference.threat_scorer import _INTENTS

    # Scan results carry an appended annotation; score only the user's message.
    text = text.split("\n\nDetected language/concepts", 1)[0]
    text = " ".join(text.split())
    base = _score(text)
    candidates: list[tuple[str, str]] = []  # (label, phrase)
    seen: set[str] = set()
    for name, _w, rx in _INTENTS:
        m = rx.search(text)
        if m and m.group(0).strip() and name not in seen:
            seen.add(name)
            candidates.append((_INTENT_LABELS.get(name, name.replace("_", " ")), m.group(0)))
    for rx, label in ((_LINK, "the link"), (_CONTACT, "the phone number / UPI ID")):
        m = rx.search(text)
        if m:
            candidates.append((label, m.group(0)))

    kept: list[tuple[str, str]] = []
    for label, phrase in candidates:  # one entry per stretch of text
        if phrase in text and not any(phrase in p or p in phrase for _l, p in kept):
            kept.append((label, phrase))
    candidates = kept[:max_parts]

    def without(keep: str | None) -> str:
        out = text
        for _label, phrase in candidates:
            if phrase != keep:
                out = out.replace(phrase, " ")
        return " ".join(out.split())

    if not candidates:
        return {"score": round(base, 4), "baseline": None, "parts": [], "redundant": False}
    baseline_text = without(None)
    baseline = _score(baseline_text) if baseline_text else 0.0
    parts = []
    for label, phrase in candidates:
        alone = _score(without(phrase))  # only this cue left in
        drop = base - _score(" ".join(text.replace(phrase, " ").split()) or ".")  # this cue taken out
        parts.append({"label": label, "phrase": phrase[:120], "score_alone": round(alone, 4),
                      "lift": round(alone - baseline, 4), "drop": round(drop, 4)})
    parts.sort(key=lambda p: p["lift"], reverse=True)
    # Redundant: no single cue matters when removed, yet removing them all does.
    redundant = all(p["drop"] < 0.05 for p in parts) and base - baseline > 0.1
    return {"score": round(base, 4), "baseline": round(baseline, 4), "parts": parts, "redundant": redundant}


# ---------------------------------------------------------------- chat timeline
_WA_LINE = re.compile(
    r"^\[?(?P<ts>\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4},?\s+\d{1,2}[:.]\d{2}(?:[:.]\d{2})?\s?(?:[APap]\.?[Mm]\.?)?)\]?\s*[-–]?\s*"
    r"(?P<who>[^:]{1,40}):\s(?P<msg>.*)$"
)
_NAME_LINE = re.compile(r"^(?P<who>[A-Za-z][\w .'+()-]{0,30}):\s+(?P<msg>.+)$")
_SKIP = re.compile(r"messages and calls are end-to-end encrypted|<media omitted>|this message was deleted|missed (voice|video) call", re.I)
MAX_CHAT_CHARS = 8000
MAX_CHAT_MESSAGES = 60
STAGE_ORDER = ("hook", "pressure", "ask", "cashout")


def split_chat(text: str) -> list[dict]:
    """Split a pasted chat into messages. Understands WhatsApp exports
    ("12/10/26, 9:41 pm - Name: text"), "Name: text" lines, and otherwise
    blank-line- or line-separated messages."""
    lines = [l.rstrip() for l in text.replace("\r\n", "\n").split("\n")]
    out: list[dict] = []
    structured = sum(1 for l in lines if _WA_LINE.match(l.strip()) or _NAME_LINE.match(l.strip()))
    if structured >= 2:
        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            m = _WA_LINE.match(line) or _NAME_LINE.match(line)
            if m:
                out.append({"sender": m.group("who").strip(), "text": m.group("msg").strip()})
            elif out:
                out[-1]["text"] += " " + line  # continuation of a multi-line message
    else:
        blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
        if len(blocks) < 2:
            blocks = [l.strip() for l in lines if l.strip()]
        out = [{"sender": "", "text": b} for b in blocks]
    return [m for m in out if m["text"] and not _SKIP.search(m["text"])][:MAX_CHAT_MESSAGES]


def chat_timeline(text: str) -> dict:
    from app_service.services.message_service import get_in_process_prediction_service
    from ml_service.inference.scam_xray import xray
    from ml_service.services.prediction_service import PredictionRequest

    svc = get_in_process_prediction_service()
    messages = split_chat(text[:MAX_CHAT_CHARS])
    if len(messages) < 2:
        raise ValueError("Paste at least two messages: a WhatsApp export, 'Name: message' lines, or one message per line.")

    first_seen: dict[str, int | None] = {s: None for s in STAGE_ORDER}
    by_sender: dict[str, int] = {}
    rows = []
    for i, m in enumerate(messages):
        res = svc.predict(PredictionRequest(text=m["text"], input_type="TEXT", metadata=None))
        xr = xray(m["text"])
        stages = [s for s in STAGE_ORDER if xr["stages"].get(s)]
        signs = [label for s in STAGE_ORDER for label in xr["stages"].get(s, [])]
        for s in stages:
            if first_seen[s] is None:
                first_seen[s] = i
        if signs and m["sender"]:
            by_sender[m["sender"]] = by_sender.get(m["sender"], 0) + len(signs)
        rows.append({"index": i, "sender": m["sender"], "text": m["text"][:600], "risk_score": round(float(res.threat_score), 4),
                     "verdict": res.verdict, "stages": stages, "signs": signs})

    whole = " \n".join(m["text"] for m in messages)
    overall = svc.predict(PredictionRequest(text=whole[:4000], input_type="TEXT", metadata=None))
    turning = next((i for i in (first_seen["ask"], first_seen["cashout"]) if i is not None), None)
    if first_seen["ask"] is not None and first_seen["cashout"] is not None:
        turning = min(first_seen["ask"], first_seen["cashout"])
    reached = [s for s in STAGE_ORDER if first_seen[s] is not None]
    first_high = next((r["index"] for r in rows if r["risk_score"] >= 0.5), None)
    suspected = max(by_sender, key=by_sender.get) if by_sender else None
    if turning is not None:
        summary = (f"The chat reaches the {'ask' if first_seen['ask'] == turning else 'cash-out'} stage at message {turning + 1}"
                   f"{(' from ' + rows[turning]['sender']) if rows[turning]['sender'] else ''}: "
                   "that is where it turns from talk into a request for something valuable.")
    elif first_high is not None:
        who = f" from {rows[first_high]['sender']}" if rows[first_high]["sender"] else ""
        summary = (f"Message {first_high + 1}{who} is the first one scored as a likely scam"
                   f"{', and the chat shows ' + ', '.join(reached) + ' signs' if reached else ''}, "
                   "but no specific request phrase (OTP, payment, link) was matched. Read the flagged messages carefully.")
    elif reached:
        summary = "Scam signs appear, but no message asks for money, details or an action yet. Be careful with what comes next."
    else:
        summary = "No scam stage was matched and no message scored as a likely scam."
    return {
        "messages": rows,
        "stage_first_seen": first_seen,
        "stages_reached": reached,
        "turning_point": turning,
        "first_high_risk": first_high,
        "suspected_sender": suspected,
        "overall": {"risk_score": round(float(overall.threat_score), 4), "verdict": overall.verdict,
                    "classifier_probability": round(float(overall.scam_probability), 4)},
        "summary": summary,
        "note": "Each message is scored on its own by the same engine as a normal scan; the overall score is for the whole chat. "
                "Stages are marked only where a matching phrase was found.",
    }
