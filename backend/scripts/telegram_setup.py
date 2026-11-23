"""Point a Telegram bot at the ScamGuard webhook (run once after deploying).

    TELEGRAM_BOT_TOKEN=123:abc TELEGRAM_WEBHOOK_SECRET=some-long-random-string \
        python scripts/telegram_setup.py https://<your-backend-host>

The same two variables must be set on the backend service. Uses only the
Telegram Bot API (setWebhook, setMyCommands, getWebhookInfo).
"""
import os
import sys

import httpx


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    token, secret = os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_WEBHOOK_SECRET"]
    api = f"https://api.telegram.org/bot{token}"
    url = sys.argv[1].rstrip("/") + f"/api/v1/telegram/webhook/{secret}"
    r = httpx.post(f"{api}/setWebhook", json={"url": url, "secret_token": secret, "allowed_updates": ["message", "edited_message"], "drop_pending_updates": True}, timeout=20)
    print("setWebhook:", r.json())
    httpx.post(f"{api}/setMyCommands", json={"commands": [{"command": "start", "description": "What ScamGuard does"},
                                                          {"command": "help", "description": "How to use it"}]}, timeout=20)
    info = httpx.get(f"{api}/getWebhookInfo", timeout=20).json()
    print("webhook:", {k: info.get("result", {}).get(k) for k in ("url", "pending_update_count", "last_error_message")})
    return 0 if r.json().get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
