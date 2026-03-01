"""add_is_active_to_portfolio_documents

Revision ID: 13fe11e5ac80
Revises: 3ea388d325ac
Create Date: 2026-01-05 18:01:19.155350

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '13fe11e5ac80'
down_revision = '3ea388d325ac'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_active column
    op.add_column('portfolio_documents', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    
    # Create indexes
    op.create_index('idx_document_active', 'portfolio_documents', ['is_active'])
    op.create_index('idx_document_company_active', 'portfolio_documents', ['company_id', 'is_active'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_document_company_active', table_name='portfolio_documents')
    op.drop_index('idx_document_active', table_name='portfolio_documents')
    
    # Drop column
    op.drop_column('portfolio_documents', 'is_active')

