"""add community_reports

Revision ID: 0006_add_community_reports
Revises: 0005_add_case_tables
"""
import sqlalchemy as sa
from alembic import op

from sqlalchemy.dialects import postgresql

revision = "0006_add_community_reports"
down_revision = "0005_add_case_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "community_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("indicator_type", sa.String(16), nullable=False),
        sa.Column("indicator_value", sa.String(255), nullable=False),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("indicator_type", "indicator_value", "reporter_id", name="uq_community_report"),
    )
    op.create_index("ix_community_reports_indicator_value", "community_reports", ["indicator_value"])
    op.create_index("ix_community_reports_reporter_id", "community_reports", ["reporter_id"])
    op.create_index("ix_community_reports_created_at", "community_reports", ["created_at"])


def downgrade() -> None:
    op.drop_table("community_reports")
