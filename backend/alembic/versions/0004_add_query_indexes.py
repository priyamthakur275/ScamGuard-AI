"""add indexes on messages.user_id and predictions.created_at

Revision ID: 0004_add_query_indexes
Revises: 42ca92f781d6
Create Date: 2026-09-21

Security/performance audit finding: Message.user_id is a foreign key hit
by every history/feedback/delete/analytics query via JOIN + WHERE, and
Prediction.created_at is range-filtered by every analytics request --
neither had an index. Postgres does not automatically index foreign key
columns (unlike the primary key), so these were full-table-scan
candidates as the predictions table grows.

NOTE: Prediction.message_id was checked too, and turned out to already be
indexed by the original 0001 migration (ix_predictions_message_id) --
verified by actually running this migration against a fresh database
before finalizing it, which caught an initial duplicate-index mistake in
an earlier draft of this file. Purely additive: no data or
application-logic changes.
"""
from alembic import op

revision = "0004_add_query_indexes"
down_revision = "42ca92f781d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_messages_user_id", "messages", ["user_id"])
    op.create_index("ix_predictions_created_at", "predictions", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_predictions_created_at", table_name="predictions")
    op.drop_index("ix_messages_user_id", table_name="messages")
