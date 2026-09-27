"""add investigation/case mode: cases, case_scan_links, case_timeline_entries

Revision ID: 0005_add_case_tables
Revises: 0004_add_query_indexes
Create Date: 2026-09-22

Phase 11: professional Investigation/Case Mode. Cases are user-owned
containers that reference existing scans (predictions) rather than
duplicating their data -- case_scan_links is a pure link table.
case_timeline_entries records real actions taken (created, status
changed, scan linked/unlinked, note added), never synthetic activity.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_add_case_tables"
down_revision = "0004_add_query_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(4000), nullable=True),
        sa.Column("severity", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
        ),
    )
    op.create_index("ix_cases_user_id", "cases", ["user_id"])
    op.create_index("ix_cases_status", "cases", ["status"])

    op.create_table(
        "case_scan_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prediction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("predictions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("case_id", "prediction_id", name="uq_case_scan_links_case_prediction"),
    )
    op.create_index("ix_case_scan_links_case_id", "case_scan_links", ["case_id"])
    op.create_index("ix_case_scan_links_prediction_id", "case_scan_links", ["prediction_id"])

    op.create_table(
        "case_timeline_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("entry_type", sa.String(24), nullable=False),
        sa.Column("content", sa.String(4000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_case_timeline_entries_case_id", "case_timeline_entries", ["case_id"])


def downgrade() -> None:
    op.drop_table("case_timeline_entries")
    op.drop_table("case_scan_links")
    op.drop_index("ix_cases_status", table_name="cases")
    op.drop_index("ix_cases_user_id", table_name="cases")
    op.drop_table("cases")
