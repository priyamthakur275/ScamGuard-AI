import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app_service.schemas.message import AnalysisResult


class CaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    severity: str = Field(default="medium")
    scan_ids: list[uuid.UUID] = Field(default_factory=list)


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    severity: str | None = None
    status: str | None = None


class CaseNoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class CaseScanLinkCreate(BaseModel):
    prediction_id: uuid.UUID


class CaseTimelineEntryRead(BaseModel):
    id: uuid.UUID
    entry_type: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseSummary(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    severity: str
    status: str
    scan_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaseDetail(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    severity: str
    status: str
    created_at: datetime
    updated_at: datetime
    scans: list[AnalysisResult]
    # Entities aggregated from the linked scans' own real, already-computed
    # highlighted_entities -- never re-derived or fabricated here.
    aggregated_entities: dict[str, list[str]]
    timeline: list[CaseTimelineEntryRead]

    model_config = {"from_attributes": True}
