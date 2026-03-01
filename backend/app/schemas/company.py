from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class CompanyBase(BaseModel):
    name: str
    market_tags: list[str] = Field(default_factory=list)
    competitors: list[str] = Field(default_factory=list)
    sources: dict = Field(default_factory=dict)


class CompanyCreate(CompanyBase):
    pass


class Company(CompanyBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class CompanyWithStats(Company):
    unread_count: int = 0
    total_items: int = 0
    last_update: Optional[datetime] = None

