"""Add currency to portfolio_metrics

Revision ID: f53264806529
Revises: 9090a4a298a5
Create Date: 2026-03-12
"""
from alembic import op
import sqlalchemy as sa

revision = 'f53264806529'
down_revision = '9090a4a298a5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('portfolio_metrics', sa.Column('currency', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('portfolio_metrics', 'currency')

