"""Add portfolio_metrics and metrics_catalog tables

Revision ID: 9090a4a298a5
Revises: 13fe11e5ac80
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '9090a4a298a5'
down_revision = '13fe11e5ac80'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('portfolio_metrics',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('period', sa.Date(), nullable=False),
        sa.Column('period_label', sa.String(), nullable=False),
        sa.Column('period_type', sa.String(), nullable=False, server_default='monthly'),
        sa.Column('is_projected', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('metrics', postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('source', sa.String(), nullable=False, server_default='salesforce_mis'),
        sa.Column('source_file', sa.String(), nullable=True),
        sa.Column('upload_batch', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_metrics_company_period', 'portfolio_metrics', ['company_id', 'period'])
    op.create_index('uq_metrics_company_period', 'portfolio_metrics', ['company_id', 'period', 'period_type', 'is_projected'], unique=True)

    op.create_table('metrics_catalog',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('raw_name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('unit', sa.String(), nullable=True),
        sa.Column('is_headline', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('sort_order', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('uq_catalog_company_metric', 'metrics_catalog', ['company_id', 'raw_name'], unique=True)


def downgrade() -> None:
    op.drop_table('metrics_catalog')
    op.drop_table('portfolio_metrics')

