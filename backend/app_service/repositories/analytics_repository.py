import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app_service.db.postgres.models import Message, Prediction

VALID_RANGES = {"24h", "7d", "30d", "all"}


def _cutoff_for_range(range_key: str) -> datetime | None:
    if range_key == "all":
        return None
    now = datetime.now(timezone.utc)
    if range_key == "24h":
        return now - timedelta(hours=24)
    if range_key == "7d":
        return now - timedelta(days=7)
    if range_key == "30d":
        return now - timedelta(days=30)
    raise ValueError(f"Unsupported analytics range: {range_key}")


class AnalyticsRepository:
    """Every method here issues a real GROUP BY / COUNT / AVG query scoped
    to Message.user_id -- the database does the counting, not a Python
    loop over whatever page of results happened to be fetched. That
    distinction is the entire point of this module: it's what makes "All
    Time" actually mean all time, not "however many rows fit on one page
    of history."
    """

    def __init__(self, db: Session):
        self.db = db

    def _base_filters(self, user_id: uuid.UUID, range_key: str) -> list:
        filters = [Message.user_id == user_id]
        cutoff = _cutoff_for_range(range_key)
        if cutoff is not None:
            filters.append(Prediction.created_at >= cutoff)
        return filters

    def total_scans(self, user_id: uuid.UUID, range_key: str) -> int:
        stmt = (
            select(func.count(Prediction.id))
            .join(Message)
            .where(*self._base_filters(user_id, range_key))
        )
        return self.db.scalar(stmt) or 0

    def group_counts(self, user_id: uuid.UUID, range_key: str, column) -> dict[str, int]:
        stmt = (
            select(column, func.count(Prediction.id))
            .join(Message)
            .where(*self._base_filters(user_id, range_key))
            .group_by(column)
        )
        rows = self.db.execute(stmt).all()
        result: dict[str, int] = {}
        for key, count in rows:
            label = key.value if hasattr(key, "value") else (key or "unknown")
            result[label] = result.get(label, 0) + count
        return result

    def feedback_counts(self, user_id: uuid.UUID, range_key: str) -> dict[str, int]:
        stmt = (
            select(Prediction.user_feedback, func.count(Prediction.id))
            .join(Message)
            .where(*self._base_filters(user_id, range_key))
            .group_by(Prediction.user_feedback)
        )
        rows = self.db.execute(stmt).all()
        counts = {"accurate": 0, "inaccurate": 0, "pending": 0}
        for feedback, count in rows:
            if feedback is True:
                counts["accurate"] += count
            elif feedback is False:
                counts["inaccurate"] += count
            else:
                counts["pending"] += count
        return counts

    def high_risk_count(self, user_id: uuid.UUID, range_key: str) -> int:
        stmt = (
            select(func.count(Prediction.id))
            .join(Message)
            .where(*self._base_filters(user_id, range_key), Prediction.risk_level == "high")
        )
        return self.db.scalar(stmt) or 0

    def averages(self, user_id: uuid.UUID, range_key: str) -> tuple[float, float]:
        stmt = (
            select(func.avg(Prediction.confidence_score), func.avg(Prediction.threat_score))
            .join(Message)
            .where(*self._base_filters(user_id, range_key))
        )
        avg_confidence, avg_threat = self.db.execute(stmt).one()
        return float(avg_confidence or 0.0), float(avg_threat or 0.0)

    def combined(self, user_id: uuid.UUID, range_key: str) -> dict:
        """Everything the summary needs in ONE query (one row per distinct
        verdict/risk/category/input/feedback combination, with counts and
        sums), aggregated here. Same results as the separate methods above,
        which cost one database round trip each."""
        stmt = (
            select(
                Prediction.verdict, Prediction.risk_level, Prediction.scam_category, Prediction.input_type,
                Prediction.user_feedback, func.count(Prediction.id),
                func.sum(Prediction.confidence_score), func.count(Prediction.confidence_score),
                func.sum(Prediction.threat_score), func.count(Prediction.threat_score),
            )
            .join(Message)
            .where(*self._base_filters(user_id, range_key))
            .group_by(Prediction.verdict, Prediction.risk_level, Prediction.scam_category, Prediction.input_type,
                      Prediction.user_feedback)
        )

        def label(key) -> str:
            return key.value if hasattr(key, "value") else (key or "unknown")

        out = {"total": 0, "verdict": {}, "risk": {}, "category": {}, "input_type": {},
               "feedback": {"accurate": 0, "inaccurate": 0, "pending": 0}, "high_risk": 0}
        conf_sum = conf_n = threat_sum = threat_n = 0.0
        for verdict, risk, category, input_type, feedback, n, c_sum, c_n, t_sum, t_n in self.db.execute(stmt).all():
            out["total"] += n
            for bucket, key in (("verdict", verdict), ("risk", risk), ("category", category), ("input_type", input_type)):
                k = label(key)
                out[bucket][k] = out[bucket].get(k, 0) + n
            out["feedback"]["accurate" if feedback is True else "inaccurate" if feedback is False else "pending"] += n
            if label(risk) == "high":
                out["high_risk"] += n
            conf_sum += float(c_sum or 0); conf_n += c_n or 0
            threat_sum += float(t_sum or 0); threat_n += t_n or 0
        out["avg_confidence"] = conf_sum / conf_n if conf_n else 0.0
        out["avg_threat"] = threat_sum / threat_n if threat_n else 0.0
        return out
