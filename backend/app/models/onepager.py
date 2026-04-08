from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base
import uuid
from datetime import datetime
import enum


class StanceEnum(str, enum.Enum):
    green = "green"
    yellow = "yellow"
    red = "red"


class CompanyOnePager(Base):
    __tablename__ = "company_onepagers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)

    # Generation metadata
    generated_at = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(String, default="ai")  # "ai" or "manual"
    is_latest = Column(Boolean, default=True, index=True)
    period_label = Column(String)  # e.g., "Mar 2026", "Q1 2026"

    # One-pager content (all editable)
    stance = Column(SQLEnum(StanceEnum), default=StanceEnum.yellow)
    stance_summary = Column(Text)
    next_milestone = Column(Text)

    # Performance update
    metrics_table = Column(JSONB)  # Array of {metric_name, current_value, previous_value, change_pct, unit}
    performance_narrative = Column(JSONB)  # Array of strings (narrative bullets)

    # Qualitative sections
    working_well = Column(JSONB)  # Array of strings
    needs_improvement = Column(JSONB)  # Array of strings
    value_creation = Column(JSONB)  # Array of strings

    # Source tracking
    data_sources = Column(JSONB)  # {metrics_periods: [...], documents_used: [...], intelligence_count: N}

    # Edit tracking
    last_edited_at = Column(DateTime)
    edit_history = Column(JSONB, default=list)  # Array of {field, old_value, new_value, edited_at}

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
