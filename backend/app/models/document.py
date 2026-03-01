from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, ForeignKey, Index, Date, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid
from app.db.base import Base


class PortfolioDocument(Base):
    __tablename__ = "portfolio_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    doc_type = Column(String, nullable=False)  # board_deck, ic_memo, diligence, quarterly_review, valuation, thesis, update, general
    document_date = Column(Date, nullable=False, index=True)
    file_path = Column(String, nullable=True)  # Nullable for Google Docs
    file_url = Column(String, nullable=True)  # Google Drive URL if synced
    file_name = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=True)  # Nullable for Google Docs
    mime_type = Column(String, nullable=False)
    full_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    tags = Column(ARRAY(String), nullable=False, default=list)
    notes = Column(Text, nullable=True)
    is_processed = Column(Boolean, default=False, nullable=False, index=True)
    uploaded_by = Column(String, nullable=True)
    
    # Hybrid system fields
    is_primary_source = Column(Boolean, default=False, nullable=False, index=True)  # True for Google Docs
    google_doc_id = Column(String, nullable=True, index=True)  # If this is a Google Doc
    requires_processing = Column(Boolean, default=True, nullable=False)  # False for reference-only uploads
    storage_purpose = Column(String, nullable=False, default='reference')  # 'primary_knowledge', 'reference', 'archive'
    is_active = Column(Boolean, default=True, nullable=False, index=True)  # True to sync this document
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    company = relationship("Company", backref="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_document_company_date", "company_id", "document_date"),
        Index("idx_document_type", "doc_type"),
        Index("idx_document_processed", "is_processed"),
        Index("idx_document_primary_source", "is_primary_source"),
        Index("idx_document_google_doc", "google_doc_id"),
        Index("idx_document_active", "is_active"),
        Index("idx_document_company_active", "company_id", "is_active"),
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_embedding = Column(Vector(1536), nullable=True)  # pgvector for semantic search
    page_number = Column(Integer, nullable=True)
    source_section = Column(String, nullable=True, index=True)  # For Google Docs: "Nov'25", "Dec'25", etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("PortfolioDocument", back_populates="chunks")

    # Indexes
    __table_args__ = (
        Index("idx_chunk_document_index", "document_id", "chunk_index"),
        Index("idx_chunk_source_section", "source_section"),
    )
