from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    """A real, server-side aggregate over ALL of the user's predictions
    matching the requested time range -- never computed from a paginated
    page of history on the frontend. See analytics_repository.py.
    """

    range: str
    total_scans: int
    verdict_distribution: dict[str, int]
    risk_distribution: dict[str, int]
    category_distribution: dict[str, int]
    input_type_distribution: dict[str, int]
    feedback_accurate: int
    feedback_inaccurate: int
    feedback_pending: int
    high_risk_count: int
    average_confidence: float
    average_threat_score: float
