import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app_service.db.base import Base
from app_service.db.types import GUID


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class SourceChannel(str, enum.Enum):
    SMS = "sms"
    EMAIL = "email"
    CHAT = "chat"
    MANUAL = "manual"


class Verdict(str, enum.Enum):
    LEGITIMATE = "legitimate"
    SPAM = "spam"
    PHISHING = "phishing"
    SCAM = "scam"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CaseSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CaseStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class CaseTimelineEntryType(str, enum.Enum):
    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    SCAN_LINKED = "scan_linked"
    SCAN_UNLINKED = "scan_unlinked"
    NOTE = "note"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False, length=16),
        default=UserRole.USER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(back_populates="user")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    text: Mapped[str] = mapped_column(String(5000), nullable=False, server_default="")
    source_channel: Mapped[SourceChannel] = mapped_column(
        Enum(SourceChannel, name="source_channel", native_enum=False, length=16),
        default=SourceChannel.MANUAL,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User | None"] = relationship(back_populates="messages")
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_name: Mapped[str] = mapped_column(String(64), nullable=False, server_default="")
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    verdict: Mapped[Verdict] = mapped_column(
        Enum(Verdict, name="verdict", native_enum=False, length=16), nullable=False
    )
    scam_probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level", native_enum=False, length=16), nullable=False
    )
    scam_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    threat_score: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    top_tokens: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    user_feedback: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ai_explanation: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    executive_summary: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    technical_explanation: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    threat_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    risk_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recommended_actions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    highlighted_entities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    similar_patterns: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    input_type: Mapped[str] = mapped_column(String(16), default="TEXT", server_default="TEXT")
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True) # use metadata_ to avoid collision with Base.metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    message: Mapped["Message"] = relationship(back_populates="predictions")
    alert: Mapped["Alert | None"] = relationship(
        back_populates="prediction", uselist=False, cascade="all, delete-orphan"
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    prediction_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    delivered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    prediction: Mapped["Prediction"] = relationship(back_populates="alert")


class ModelRegistryMeta(Base):
    __tablename__ = "model_registry_meta"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    precision: Mapped[float] = mapped_column(Float, nullable=False)
    recall: Mapped[float] = mapped_column(Float, nullable=False)
    f1: Mapped[float] = mapped_column(Float, nullable=False)
    is_production: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    log_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Case(Base):
    """Investigation/case mode (Phase 11). A case is a user-owned
    container linking one or more existing scans (Predictions) together
    for an ongoing investigation -- it does not duplicate scan data, it
    references it (see CaseScanLink), and entities are aggregated at read
    time from the linked scans' own highlighted_entities (already real,
    already computed -- never re-fabricated here).
    """
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    severity: Mapped[CaseSeverity] = mapped_column(
        Enum(CaseSeverity, name="case_severity", native_enum=False, length=16),
        default=CaseSeverity.MEDIUM,
        nullable=False,
    )
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, name="case_status", native_enum=False, length=16),
        default=CaseStatus.OPEN,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    scan_links: Mapped[list["CaseScanLink"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    timeline_entries: Mapped[list["CaseTimelineEntry"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="CaseTimelineEntry.created_at"
    )


class CaseScanLink(Base):
    """Links a Case to an existing Prediction (a real, already-analyzed
    scan) -- many-to-many capable (one scan can be relevant to more than
    one case), never a copy of the scan's data.
    """
    __tablename__ = "case_scan_links"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prediction_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    case: Mapped["Case"] = relationship(back_populates="scan_links")
    prediction: Mapped["Prediction"] = relationship()


class CaseTimelineEntry(Base):
    """A real investigation timeline: every entry here corresponds to an
    actual action taken (case created, status changed, a scan linked or
    unlinked, a note added) -- never synthetic/placeholder activity.
    """
    __tablename__ = "case_timeline_entries"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    entry_type: Mapped[CaseTimelineEntryType] = mapped_column(
        Enum(CaseTimelineEntryType, name="case_timeline_entry_type", native_enum=False, length=24),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(String(4000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    case: Mapped["Case"] = relationship(back_populates="timeline_entries")
