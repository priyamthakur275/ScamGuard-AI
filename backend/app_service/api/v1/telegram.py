"""Telegram webhook (v2). Disabled (404) unless TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET are set."""
import hmac

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app_service.core.config import get_settings
from app_service.core.rate_limit import limiter
from app_service.db.session import get_db
from app_service.services import telegram_bot
from app_service.services.extraction import ExtractionService
from app_service.services.message_service import MessageService

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook/{secret}")
@limiter.limit("60/minute")
def webhook(request: Request, secret: str, background: BackgroundTasks, update: dict = Body(...), db: Session = Depends(get_db),
            x_telegram_bot_api_secret_token: str | None = Header(default=None)) -> dict:
    s = get_settings()
    if not (s.TELEGRAM_BOT_TOKEN and s.TELEGRAM_WEBHOOK_SECRET) or not hmac.compare_digest(secret, s.TELEGRAM_WEBHOOK_SECRET):
        raise HTTPException(status_code=404)
    if x_telegram_bot_api_secret_token is not None and not hmac.compare_digest(x_telegram_bot_api_secret_token, s.TELEGRAM_WEBHOOK_SECRET):
        raise HTTPException(status_code=404)

    def analyze(text: str) -> dict:
        t, metadata = ExtractionService.extract(None, text, "TEXT")
        result = MessageService(db).analyze_ephemeral(t, "TEXT", {**(metadata or {}), "channel": "telegram"})
        return result.model_dump(mode="json")

    chat_id, reply = telegram_bot.handle_update(update, analyze)
    if chat_id is not None and reply:
        background.add_task(telegram_bot.send, chat_id, reply)
    return {"ok": True}
