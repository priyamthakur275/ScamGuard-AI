import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    input_type: str = "TEXT"

    @field_validator("text", mode="before")
    @classmethod
    def truncate_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("text must not be blank")
        if len(value) > 4500:
            return value[:4500]
        return value


class TokenContribution(BaseModel):
    token: str
    weight: float


class AnalysisResult(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    text: str
    input_type: str
    metadata: dict | None = None
    verdict: str
    scam_probability: float
    risk_level: str
    scam_category: str | None
    confidence_score: float
    threat_score: float
    top_contributing_tokens: list[TokenContribution]
    model_name: str
    model_version: str
    latency_ms: float
    user_feedback: bool | None
    ai_explanation: str | None = None
    executive_summary: str | None = None
    technical_explanation: str | None = None
    threat_level: str | None = None
    risk_breakdown: dict | None = None
    recommended_actions: list | None = None
    highlighted_entities: dict | None = None
    similar_patterns: list | None = None
    created_at: datetime


class FeedbackRequest(BaseModel):
    is_accurate: bool
