from sqlalchemy import Column, String, Text, DateTime, Boolean, Float, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSON
import uuid
from app.db.base import Base

class IntelligenceItem(Base):
    __tablename__ = "intelligence_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    title = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    full_content = Column(Text, nullable=True)
    source_type = Column(String, nullable=False)  # "blog", "twitter", "g2", "reddit", etc.
    source_url = Column(Text, unique=True, nullable=False, index=True)
    result_category = Column(String, nullable=True)  # "product", "gtm", "traction", etc.
    published_date = Column(DateTime(timezone=True), nullable=True, index=True)
    captured_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    relevance_score = Column(Float, default=0.0)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    extra_data = Column(JSON)

    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_company_published", "company_id", "published_date"),
        Index("idx_company_read", "company_id", "is_read"),
    )

