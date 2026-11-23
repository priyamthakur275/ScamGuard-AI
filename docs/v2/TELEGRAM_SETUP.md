# ScamGuard Telegram bot: setup (about 5 minutes)

The bot runs inside the existing backend as a webhook (`/api/v1/telegram/webhook/<secret>`), so it needs no extra
server and costs nothing. It is off until two settings are added. Messages go through the same pipeline as the
website's no-login quick check; nothing is stored and message text is never logged.

1. In Telegram, open **@BotFather** → `/newbot` → pick a name (e.g. *ScamGuard India*) and a username ending in `bot`.
   Copy the token it gives you.
2. Make a long random secret, for example: `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
3. On Render, open the **backend** service → Environment → add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET`
   → Save (it redeploys).
4. From `backend/`, run once:

       TELEGRAM_BOT_TOKEN=... TELEGRAM_WEBHOOK_SECRET=... python scripts/telegram_setup.py https://<backend-host>

   It prints `setWebhook: {'ok': True, ...}` when it works.
5. Message your bot `/start`, then forward it any SMS.

The free Render instance sleeps after 15 minutes; the existing keep-alive workflow pings it. If a reply takes
about 30 seconds the first time, that is the server waking up; Telegram retries the webhook on its own.
