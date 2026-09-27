"""add message text and prediction result/feedback fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-24

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("text", sa.String(5000), nullable=False, server_default=""))
    op.add_column(
        "predictions", sa.Column("model_name", sa.String(64), nullable=False, server_default="")
    )
    op.add_column(
        "predictions", sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0")
    )
    op.add_column(
        "predictions", sa.Column("threat_score", sa.Float(), nullable=False, server_default="0")
    )
    op.add_column(
        "predictions", sa.Column("top_tokens", sa.JSON(), nullable=False, server_default="[]")
    )
    op.add_column("predictions", sa.Column("user_feedback", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("predictions", "user_feedback")
    op.drop_column("predictions", "top_tokens")
    op.drop_column("predictions", "threat_score")
    op.drop_column("predictions", "confidence_score")
    op.drop_column("predictions", "model_name")
    op.drop_column("messages", "text")
