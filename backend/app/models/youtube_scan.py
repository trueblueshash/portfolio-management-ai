from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base
import uuid
from datetime import datetime


class YouTubeScan(Base):
    __tablename__ = "youtube_scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    video_id = Column(String, nullable=False)
    video_title = Column(String)
    video_url = Column(String)
    channel_name = Column(String)
    published_at = Column(DateTime)
    search_query = Column(String)
    transcript_text = Column(Text)
    transcript_length = Column(Integer)
    processed = Column(Boolean, default=False)
    relevance_score = Column(Integer, default=0)
    insights = Column(JSONB, default=list)
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
