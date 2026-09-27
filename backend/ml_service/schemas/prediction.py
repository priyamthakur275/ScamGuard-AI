from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Verdict = Literal["legitimate", "spam", "phishing", "scam"]
RiskLevel = Literal["low", "medium", "high"]


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    input_type: str = "TEXT"
    metadata: dict | None = None

    @field_validator("text", mode="before")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("text must not be blank")
        if len(value) > 4500:
            return value[:4500]
        return value


class FeatureContributionResponse(BaseModel):
    token: str
    weight: float


class PredictResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    verdict: Verdict
    input_type: str = "TEXT"
    metadata: dict | None = None
    scam_probability: float
    risk_level: RiskLevel
    scam_category: str | None
    confidence_score: float
    threat_score: float
    top_contributing_tokens: list[FeatureContributionResponse]
    model_name: str
    model_version: str
    latency_ms: float
    ai_explanation: str | None = None
    executive_summary: str | None = None
    technical_explanation: str | None = None
    threat_level: str | None = None
    risk_breakdown: dict | None = None
    recommended_actions: list[str] | None = None
    highlighted_entities: dict | None = None
    similar_patterns: list[dict] | None = None


class ModelInfoResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    version: str
    is_production: bool
    trained_at: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    false_positive_rate: float
