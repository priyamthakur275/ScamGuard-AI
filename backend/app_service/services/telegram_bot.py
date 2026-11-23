"""ScamGuard on Telegram (v2): forward or paste a message, get a verdict.

Runs as a webhook inside the existing backend, so it needs no extra server.
Every message goes through the same pipeline as the website's no-login quick
check (``MessageService.analyze_ephemeral``): nothing is stored, and message
text is never logged. Only text is checked; for screenshots the bot points to
the website, which has OCR.
"""
from __future__ import annotations

import html
import logging

import httpx

from app_service.core.config import get_settings

logger = logging.getLogger(__name__)

SITE = "https://scamguard-frontend-r6t7.onrender.com"
MAX_LEN = 2000

WELCOME = (
    "<b>ScamGuard</b> checks messages for scams.\n\n"
    "Forward me a suspicious SMS, WhatsApp or email text, or paste it here. "
    "I reply with a verdict, the warning signs I found, and what to do.\n\n"
    "English, Hindi and Hinglish work. Nothing you send is stored.\n\n"
    "Lost money? Call <b>1930</b> or report at cybercrime.gov.in within the first hour."
)
HELP = (
    "<b>How to use</b>\n"
    "• Forward a message to me, or paste its text.\n"
    "• Screenshots: use the website, which reads images: " + SITE + "\n"
    "• /start shows the welcome message.\n\n"
    "ScamGuard is an aid, not a guarantee. When in doubt, call the official number on your card or the company's website."
)


def format_reply(result: dict) -> str:
    """Turn an AnalysisResult dict into a short Telegram HTML message."""
    scam = str(result.get("verdict", "")).lower() != "legitimate"
    score = float(result.get("threat_score") or 0.0)
    level = str(result.get("risk_level") or "").lower()
    category = (result.get("scam_category") or "").replace("_", " ")
    head = (f"🚨 <b>Likely scam</b>{(' · ' + html.escape(category)) if category else ''}" if scam else "✅ <b>Looks genuine</b>")
    lines = [head, f"Scam likelihood: <b>{round(score * 100)}%</b>" + (f" ({html.escape(level)} risk)" if level else "")]
    if 0.3 <= score < 0.7:
        lines.append("⚠️ <i>Not sure. Check with the official number before you act.</i>")
    spans = ((result.get("metadata") or {}).get("xray") or {}).get("spans") or []
    signs, seen = [], set()
    for s in spans:
        label = s.get("label")
        if label and label not in seen:
            seen.add(label)
            signs.append(f"• {html.escape(label)}: {html.escape(s.get('why', ''))}")
    if scam and signs:
        lines += ["", "<b>Warning signs</b>", *signs[:4]]
    actions = [a for a in (result.get("recommended_actions") or []) if isinstance(a, str)]
    if scam:
        lines += ["", "<b>What to do</b>", *[f"• {html.escape(a)}" for a in actions[:3]]]
        lines.append("• Lost money? Call <b>1930</b> now or report at cybercrime.gov.in.")
    lines += ["", f"Full report: {SITE}"]
    return "\n".join(lines)


def _message_text(update: dict) -> tuple[int | None, str | None, bool]:
    msg = update.get("message") or update.get("edited_message") or update.get("channel_post") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    text = msg.get("text") or msg.get("caption")
    has_media = any(k in msg for k in ("photo", "document", "voice", "video", "audio"))
    return chat_id, text, has_media


def handle_update(update: dict, analyze) -> tuple[int | None, str | None]:
    """Pure function: Telegram update -> (chat_id, reply). ``analyze(text) -> dict``."""
    chat_id, text, has_media = _message_text(update)
    if chat_id is None:
        return None, None
    if not text:
        return chat_id, ("I can read text only. For a screenshot, open " + SITE + " and upload it there." if has_media else HELP)
    t = text.strip()
    if t.startswith("/start"):
        return chat_id, WELCOME
    if t.startswith("/help"):
        return chat_id, HELP
    if len(t) < 3:
        return chat_id, "Please send the full message you want me to check."
    try:
        return chat_id, format_reply(analyze(t[:MAX_LEN]))
    except Exception:
        logger.exception("Telegram analysis failed")
        return chat_id, "Sorry, I could not check that right now. Please try again in a minute."


def send(chat_id: int, text: str) -> None:
    token = get_settings().TELEGRAM_BOT_TOKEN
    if not token:
        return
    try:
        httpx.post(f"https://api.telegram.org/bot{token}/sendMessage",
                   json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=10)
    except Exception:
        logger.warning("Telegram sendMessage failed", exc_info=False)
