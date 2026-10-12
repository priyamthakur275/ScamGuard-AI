from datetime import datetime, timezone

from app_service.services.keep_alive import in_window


def _utc(h, m=0):
    return datetime(2026, 10, 13, h, m, tzinfo=timezone.utc)


def test_window_is_in_india_time():
    # 03:30 UTC = 09:00 IST (inside 08:00-22:00); 17:00 UTC = 22:30 IST (outside)
    assert in_window(_utc(3, 30), "08:00-22:00")
    assert not in_window(_utc(17, 0), "08:00-22:00")
    assert not in_window(_utc(2, 0), "08:00-22:00")  # 07:30 IST


def test_window_crossing_midnight():
    assert in_window(_utc(19, 0), "22:00-02:00")  # 00:30 IST
    assert not in_window(_utc(6, 0), "22:00-02:00")  # 11:30 IST
