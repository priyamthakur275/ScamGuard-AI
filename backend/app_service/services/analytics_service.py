import uuid

from sqlalchemy.orm import Session

from app_service.core.exceptions import ValidationAppError
from app_service.db.postgres.models import Prediction
from app_service.repositories.analytics_repository import AnalyticsRepository, VALID_RANGES
from app_service.schemas.analytics import AnalyticsSummary


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AnalyticsRepository(db)

    def summary(self, user_id: uuid.UUID, range_key: str) -> AnalyticsSummary:
        if range_key not in VALID_RANGES:
            raise ValidationAppError(
                f"Invalid range '{range_key}'. Must be one of: {', '.join(sorted(VALID_RANGES))}."
            )

        total = self.repo.total_scans(user_id, range_key)
        verdict_dist = self.repo.group_counts(user_id, range_key, Prediction.verdict)
        risk_dist = self.repo.group_counts(user_id, range_key, Prediction.risk_level)
        category_dist = self.repo.group_counts(user_id, range_key, Prediction.scam_category)
        input_type_dist = self.repo.group_counts(user_id, range_key, Prediction.input_type)
        feedback = self.repo.feedback_counts(user_id, range_key)
        high_risk = self.repo.high_risk_count(user_id, range_key)
        avg_confidence, avg_threat = self.repo.averages(user_id, range_key)

        return AnalyticsSummary(
            range=range_key,
            total_scans=total,
            verdict_distribution=verdict_dist,
            risk_distribution=risk_dist,
            category_distribution={k: v for k, v in category_dist.items() if k != "unknown"},
            input_type_distribution=input_type_dist,
            feedback_accurate=feedback["accurate"],
            feedback_inaccurate=feedback["inaccurate"],
            feedback_pending=feedback["pending"],
            high_risk_count=high_risk,
            average_confidence=round(avg_confidence, 4),
            average_threat_score=round(avg_threat, 4),
        )
