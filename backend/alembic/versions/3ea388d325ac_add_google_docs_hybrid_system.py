"""add_google_docs_hybrid_system

Revision ID: 3ea388d325ac
Revises: 
Create Date: 2026-01-05 13:02:47.588588

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = '3ea388d325ac'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add Google Doc fields to companies table
    op.add_column('companies', sa.Column('primary_gdoc_id', sa.String(), nullable=True))
    op.add_column('companies', sa.Column('primary_gdoc_url', sa.String(), nullable=True))
    op.add_column('companies', sa.Column('gdoc_sync_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('companies', sa.Column('gdoc_last_synced', sa.DateTime(timezone=True), nullable=True))
    op.add_column('companies', sa.Column('gdoc_sync_frequency_minutes', sa.Integer(), nullable=False, server_default='60'))
    
    # Add hybrid system fields to portfolio_documents table
    op.add_column('portfolio_documents', sa.Column('is_primary_source', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('portfolio_documents', sa.Column('google_doc_id', sa.String(), nullable=True))
    op.add_column('portfolio_documents', sa.Column('requires_processing', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('portfolio_documents', sa.Column('storage_purpose', sa.String(), nullable=False, server_default='reference'))
    
    # Make file_path and file_size_bytes nullable for Google Docs
    op.alter_column('portfolio_documents', 'file_path', nullable=True)
    op.alter_column('portfolio_documents', 'file_size_bytes', nullable=True)
    
    # Add source_section to document_chunks table
    op.add_column('document_chunks', sa.Column('source_section', sa.String(), nullable=True))
    
    # Create indexes
    op.create_index('ix_portfolio_documents_is_primary_source', 'portfolio_documents', ['is_primary_source'])
    op.create_index('ix_portfolio_documents_google_doc_id', 'portfolio_documents', ['google_doc_id'])
    op.create_index('ix_document_chunks_source_section', 'document_chunks', ['source_section'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_document_chunks_source_section', table_name='document_chunks')
    op.drop_index('ix_portfolio_documents_google_doc_id', table_name='portfolio_documents')
    op.drop_index('ix_portfolio_documents_is_primary_source', table_name='portfolio_documents')
    
    # Remove columns from document_chunks
    op.drop_column('document_chunks', 'source_section')
    
    # Restore nullable constraints
    op.alter_column('portfolio_documents', 'file_size_bytes', nullable=False)
    op.alter_column('portfolio_documents', 'file_path', nullable=False)
    
    # Remove columns from portfolio_documents
    op.drop_column('portfolio_documents', 'storage_purpose')
    op.drop_column('portfolio_documents', 'requires_processing')
    op.drop_column('portfolio_documents', 'google_doc_id')
    op.drop_column('portfolio_documents', 'is_primary_source')
    
    # Remove columns from companies
    op.drop_column('companies', 'gdoc_sync_frequency_minutes')
    op.drop_column('companies', 'gdoc_last_synced')
    op.drop_column('companies', 'gdoc_sync_enabled')
    op.drop_column('companies', 'primary_gdoc_url')
    op.drop_column('companies', 'primary_gdoc_id')
