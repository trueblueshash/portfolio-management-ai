from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class IntelligenceItemBase(BaseModel):
    title: str
    summary: Optional[str] = None
    full_content: Optional[str] = None
    source_type: str
    source_url: str
    result_category: Optional[str] = None
    published_date: Optional[datetime] = None
    relevance_score: float = 0.0
    is_read: bool = False
    extra_data: Optional[Dict[str, Any]] = None


class IntelligenceItemCreate(IntelligenceItemBase):
    company_id: UUID


class IntelligenceItem(IntelligenceItemBase):
    id: UUID
    company_id: UUID
    captured_date: datetime

    class Config:
        from_attributes = True


class IntelligenceItemUpdate(BaseModel):
    is_read: Optional[bool] = None

