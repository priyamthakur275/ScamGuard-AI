"""add_user_fields

Revision ID: 42ca92f781d6
Revises: 0002
Create Date: 2026-08-19 12:57:50.360094

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '42ca92f781d6'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # predictions
    op.add_column('predictions', sa.Column('ai_explanation', sa.String(length=2000), nullable=True))
    op.add_column('predictions', sa.Column('executive_summary', sa.String(length=1000), nullable=True))
    op.add_column('predictions', sa.Column('technical_explanation', sa.String(length=2000), nullable=True))
    op.add_column('predictions', sa.Column('threat_level', sa.String(length=16), nullable=True))
    op.add_column('predictions', sa.Column('risk_breakdown', sa.JSON(), nullable=True))
    op.add_column('predictions', sa.Column('recommended_actions', sa.JSON(), nullable=True))
    op.add_column('predictions', sa.Column('highlighted_entities', sa.JSON(), nullable=True))
    op.add_column('predictions', sa.Column('similar_patterns', sa.JSON(), nullable=True))
    op.add_column('predictions', sa.Column('input_type', sa.String(length=16), server_default='TEXT', nullable=False))
    op.add_column('predictions', sa.Column('metadata', sa.JSON(), nullable=True))
    
    # users
    op.add_column('users', sa.Column('full_name', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('preferences', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # users
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'preferences')
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'full_name')
    
    # predictions
    op.drop_column('predictions', 'metadata')
    op.drop_column('predictions', 'input_type')
    op.drop_column('predictions', 'similar_patterns')
    op.drop_column('predictions', 'highlighted_entities')
    op.drop_column('predictions', 'recommended_actions')
    op.drop_column('predictions', 'risk_breakdown')
    op.drop_column('predictions', 'threat_level')
    op.drop_column('predictions', 'technical_explanation')
    op.drop_column('predictions', 'executive_summary')
    op.drop_column('predictions', 'ai_explanation')
