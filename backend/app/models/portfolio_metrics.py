"""
Portfolio metrics - stores structured MIS data from Excel uploads.
Uses JSONB for flexible per-company metrics.
"""
from sqlalchemy import Column, String, Text, DateTime, Date, Boolean, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base


class PortfolioMetrics(Base):
    __tablename__ = "portfolio_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)

    # Period info
    period = Column(Date, nullable=False)
    period_label = Column(String, nullable=False)  # "Sep'25", "FY25"
    period_type = Column(String, nullable=False, default="monthly")  # monthly, quarterly, annual
    is_projected = Column(Boolean, default=False, nullable=False)

    # All metrics as flexible JSONB — keys are metric names, values are numbers
    # Example: {"Exit ARR": 7266400.8, "Gross Margin": 0.8, "Burn Multiple": 0.3, ...}
    metrics = Column(JSONB, nullable=False, default=dict)

    # Source tracking
    source = Column(String, nullable=False, default="salesforce_mis")
    source_file = Column(String, nullable=True)
    upload_batch = Column(String, nullable=True)  # Groups metrics from same upload: "20260309_scrut_automation"

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    company = relationship("Company", backref="metrics")

    __table_args__ = (
        Index("idx_metrics_company_period", "company_id", "period"),
        Index("uq_metrics_company_period", "company_id", "period", "period_type", "is_projected", unique=True),
    )


class MetricsCatalog(Base):
    """Maps raw metric names to standard categories per company.
    Each company has its own catalog since metric names differ."""
    __tablename__ = "metrics_catalog"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)

    raw_name = Column(String, nullable=False)          # Original name from MIS: "Exit ARR"
    display_name = Column(String, nullable=False)       # Cleaned display: "ARR"
    category = Column(String, nullable=False)           # revenue, growth, retention, unit_economics, cash, team, pipeline, customers, product, risk, engagement, other
    unit = Column(String, nullable=True)                # "$", "$K", "$Mn", "%", "#", "x", "months"
    is_headline = Column(Boolean, default=False)        # Show in top-level company summary card
    sort_order = Column(String, nullable=True)          # For display ordering within category

    company = relationship("Company", backref="metrics_catalog")

    __table_args__ = (
        Index("uq_catalog_company_metric", "company_id", "raw_name", unique=True),
    )
