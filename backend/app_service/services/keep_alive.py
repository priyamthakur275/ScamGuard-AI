"""Keeps the backend awake on Render's free plan.

Render spins a free web service down after 15 minutes without inbound
traffic, and waking a sleeping backend has proved unreliable (requests got
502/429 for hours and the container never started). So the backend keeps
*itself* awake: every 9 minutes inside the configured window it requests its
own public /api/v1/health URL, which is inbound traffic through Render's edge.

It pings the backend directly, not through the frontend, so the frontend is
awake only while people actually use it. Render's free plan gives 750
instance-hours per month for the whole workspace and suspends every free
service when they run out: the backend awake 19 h/day (06:00-01:00 IST) is
~590 h, leaving room for the frontend's real visits.
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


# Kept for an optional future cutover; None = follow the configured window,
# which now defaults to around the clock (see config.KEEPALIVE_WINDOW_IST).
ALWAYS_ON_FROM: datetime | None = None


def in_window(now: datetime, spec: str, always_on_from: datetime | None = None) -> bool:
    if always_on_from is not None and now >= always_on_from:
        return True
    start, end = parse_window(spec)
    if start == end:  # e.g. "00:00-00:00" = around the clock
        return True
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
                if in_window(datetime.now(timezone.utc), window, ALWAYS_ON_FROM):
                    resp = await client.get(url)
                    logger.info("Keep-alive ping %s -> %s", url, resp.status_code)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # network blips must never kill the loop
                logger.warning("Keep-alive ping failed: %s", exc)
            await asyncio.sleep(INTERVAL_SECONDS)
