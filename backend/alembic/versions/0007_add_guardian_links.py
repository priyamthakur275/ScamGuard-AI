"""add guardian_links

Revision ID: 0007_add_guardian_links
Revises: 0006_add_community_reports
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_add_guardian_links"
down_revision = "0006_add_community_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guardian_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("protected_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("guardian_email", sa.String(255), nullable=False),
        sa.Column("guardian_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("protected_id", "guardian_email", name="uq_guardian_link"),
    )
    op.create_index("ix_guardian_links_protected_id", "guardian_links", ["protected_id"])
    op.create_index("ix_guardian_links_guardian_email", "guardian_links", ["guardian_email"])
    op.create_index("ix_guardian_links_guardian_id", "guardian_links", ["guardian_id"])


def downgrade() -> None:
    op.drop_table("guardian_links")
