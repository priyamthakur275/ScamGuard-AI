"""Telegram webhook (v2)."""
import pytest

from app_service.core.config import get_settings
from app_service.services import telegram_bot


def _update(text=None, **extra):
    msg = {"message_id": 1, "chat": {"id": 42, "type": "private"}, **extra}
    if text is not None:
        msg["text"] = text
    return {"update_id": 1, "message": msg}


def test_commands_and_media():
    assert telegram_bot.handle_update(_update("/start"), None) == (42, telegram_bot.WELCOME)
    assert telegram_bot.handle_update(_update("/help"), None) == (42, telegram_bot.HELP)
    chat, reply = telegram_bot.handle_update(_update(photo=[{"file_id": "x"}]), None)
    assert chat == 42 and "text only" in reply
    assert telegram_bot.handle_update({"update_id": 2}, None) == (None, None)


def test_scam_reply_has_signs_actions_and_helpline():
    result = {"verdict": "scam", "threat_score": 0.97, "risk_level": "high", "scam_category": "banking_fraud",
              "recommended_actions": ["Do not share the OTP.", "Block the sender."],
              "metadata": {"xray": {"spans": [{"label": "Asks for OTP / PIN / password", "why": "No bank asks for these."}]}}}
    reply = telegram_bot.format_reply(result)
    assert "Likely scam" in reply and "banking fraud" in reply and "97%" in reply
    assert "Asks for OTP" in reply and "Do not share the OTP." in reply and "1930" in reply


def test_genuine_and_uncertain_replies():
    assert "Looks genuine" in telegram_bot.format_reply({"verdict": "legitimate", "threat_score": 0.05})
    assert "Not sure" in telegram_bot.format_reply({"verdict": "legitimate", "threat_score": 0.45})


def test_html_is_escaped():
    reply = telegram_bot.format_reply({"verdict": "scam", "threat_score": 0.9, "scam_category": "<b>x</b>",
                                       "metadata": {"xray": {"spans": [{"label": "<i>", "why": "a&b"}]}}})
    assert "<b>x</b>" not in reply and "&lt;b&gt;" in reply and "a&amp;b" in reply


def test_analysis_error_gives_friendly_reply():
    def boom(_):
        raise RuntimeError("down")
    assert "could not check" in telegram_bot.handle_update(_update("Your KYC is pending, click here"), boom)[1]


def test_webhook_disabled_without_token(client):
    assert client.post("/api/v1/telegram/webhook/anything", json=_update("hi there")).status_code == 404


def test_webhook_end_to_end(client, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setattr(s, "TELEGRAM_WEBHOOK_SECRET", "s3cret-value")
    sent = []
    monkeypatch.setattr(telegram_bot, "send", lambda chat_id, text: sent.append((chat_id, text)))
    assert client.post("/api/v1/telegram/webhook/wrong", json=_update("x")).status_code == 404
    assert client.post("/api/v1/telegram/webhook/s3cret-value", json=_update("x"), headers={"X-Telegram-Bot-Api-Secret-Token": "bad"}).status_code == 404
    r = client.post("/api/v1/telegram/webhook/s3cret-value", headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret-value"},
                    json=_update("Aapka SBI account aaj band ho jayega. OTP batayein turant: http://sbi-kyc.xyz"))
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert sent and sent[0][0] == 42 and "Likely scam" in sent[0][1]
