from sqlalchemy import Column, String, DateTime, JSON, Boolean, Integer, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
import uuid
from app.db.base import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False, index=True)
    market_tags = Column(ARRAY(String), nullable=False, default=list)
    competitors = Column(ARRAY(String), nullable=False, default=list)
    sources = Column(JSON, nullable=False, default=dict)
    comp_tickers = Column(JSONB, default=dict)  # {"CompanyName": "TICKER" or null}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Google Doc integration fields
    # NOTE: primary_gdoc_id and primary_gdoc_url are DEPRECATED - kept for backward compatibility only
    # Companies now have multiple Google Docs stored in PortfolioDocument table
    # The "latest" document is determined by document_date, not a primary flag
    primary_gdoc_id = Column(String, nullable=True)  # DEPRECATED: Use PortfolioDocument.google_doc_id instead
    primary_gdoc_url = Column(String, nullable=True)  # DEPRECATED: Use PortfolioDocument.file_url instead
    gdoc_sync_enabled = Column(Boolean, default=False, nullable=False)  # Enable auto-sync for all active docs
    gdoc_last_synced = Column(DateTime(timezone=True), nullable=True)  # Last sync time for any doc
    gdoc_sync_frequency_minutes = Column(Integer, default=60, nullable=False)  # How often to sync

