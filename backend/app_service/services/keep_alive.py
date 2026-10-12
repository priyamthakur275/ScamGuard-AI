"""Keeps the Render free-tier services awake during presentation hours.

Render spins a free web service down after 15 minutes without inbound
traffic, and the GitHub Actions cron meant to prevent that is only run
every few hours in practice (scheduled workflows are best-effort). So the
backend keeps *itself* awake: every 9 minutes inside the configured window
it calls the public frontend URL's /backend-api health route. That one
request is inbound traffic for both services (frontend proxy -> backend),
so neither goes to sleep while the window is open.

The window exists because Render's free plan gives 750 instance-hours per
month across all free services; two services awake 24/7 would use ~1,490.
08:00-22:00 IST for both services is ~28 h/day, which fits the budget.
Outside the window the services sleep normally and wake on the first visit.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timedelta, timezone

import httpx

logger = logging.getLogger("app_service.keep_alive")
IST = timezone(timedelta(hours=5, minutes=30))
INTERVAL_SECONDS = 9 * 60


def parse_window(spec: str) -> tuple[time, time]:
    start, end = (part.strip() for part in spec.split("-", 1))
    return time.fromisoformat(start), time.fromisoformat(end)


def in_window(now: datetime, spec: str) -> bool:
    start, end = parse_window(spec)
    current = now.astimezone(IST).time()
    if start <= end:
        return start <= current < end
    return current >= start or current < end  # window crosses midnight


async def keep_alive_loop(url: str, window: str, first_delay: float = 60) -> None:
    logger.info("Keep-alive active: pinging %s every %ss during %s IST", url, INTERVAL_SECONDS, window)
    await asyncio.sleep(first_delay)  # let the server finish binding first
    async with httpx.AsyncClient(timeout=90, follow_redirects=True) as client:
        while True:
            try:
                if in_window(datetime.now(timezone.utc), window):
                    resp = await client.get(url)
                    logger.info("Keep-alive ping %s -> %s", url, resp.status_code)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # network blips must never kill the loop
                logger.warning("Keep-alive ping failed: %s", exc)
            await asyncio.sleep(INTERVAL_SECONDS)
