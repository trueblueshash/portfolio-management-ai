from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base
import uuid
from datetime import datetime


class PublicComp(Base):
    __tablename__ = "public_comps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    comp_name = Column(String, nullable=False)
    ticker = Column(String)
    is_portfolio_company = Column(Boolean, default=False)

    revenue_ttm_millions = Column(Float)
    revenue_currency = Column(String, default="USD")
    revenue_growth_pct = Column(Float)
    gross_margin_pct = Column(Float)
    operating_margin_pct = Column(Float)
    fcf_margin_pct = Column(Float)
    sm_pct_of_revenue = Column(Float)
    rd_pct_of_revenue = Column(Float)
    rule_of_40 = Column(Float)
    nrr_pct = Column(Float)
    employees = Column(Integer)
    revenue_per_employee_k = Column(Float)

    data_source = Column(String, default="yfinance")
    fiscal_period = Column(String)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    is_latest = Column(Boolean, default=True, index=True)
    raw_data = Column(JSONB)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
