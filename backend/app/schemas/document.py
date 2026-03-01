from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID
from enum import Enum


class DocumentType(str, Enum):
    BOARD_DECK = "board_deck"
    IC_MEMO = "ic_memo"
    DILIGENCE = "diligence"
    QUARTERLY_REVIEW = "quarterly_review"
    VALUATION = "valuation"
    THESIS = "thesis"
    UPDATE = "update"
    GENERAL = "general"


class DocumentUploadRequest(BaseModel):
    company_id: Optional[UUID] = None  # None for fund-level docs
    title: str
    doc_type: DocumentType
    document_date: date
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class DocumentResponse(BaseModel):
    id: UUID
    company_id: Optional[UUID] = None
    company_name: Optional[str] = None
    title: str
    doc_type: str
    document_date: date
    file_path: Optional[str] = None  # None for Google Docs
    file_url: Optional[str] = None  # Google Doc URL or file URL
    file_name: Optional[str] = None  # None for Google Docs
    file_size_bytes: Optional[int] = None  # None for Google Docs
    mime_type: str
    full_text: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str]
    notes: Optional[str] = None
    is_processed: bool
    uploaded_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    processing_status: str  # "processed", "processing", "failed", "pending"
    # Google Doc fields
    google_doc_id: Optional[str] = None
    is_primary_source: Optional[bool] = False
    is_active: Optional[bool] = True

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


class DocumentSearchRequest(BaseModel):
    query: str
    company_id: Optional[UUID] = None
    doc_type: Optional[str] = None
    limit: int = Field(default=5, ge=1, le=20)


class DocumentSearchResult(BaseModel):
    chunk_text: str
    document_title: str
    company_name: Optional[str]
    page_number: Optional[int]
    similarity_score: float
    document_id: UUID


class DocumentQuestionRequest(BaseModel):
    question: str
    company_id: Optional[UUID] = None
    doc_type: Optional[str] = None
    search_scope: str = Field(default="primary_only")  # 'primary_only', 'all', 'reference_only'


class DocumentCitation(BaseModel):
    document_title: str
    company_name: Optional[str]
    page_number: Optional[int]
    chunk_text: str


class DocumentQuestionResponse(BaseModel):
    answer: str
    sources: List[DocumentCitation]
    confidence: float = 0.0


class DocumentMetadataUpdate(BaseModel):
    title: Optional[str] = None
    doc_type: Optional[DocumentType] = None
    document_date: Optional[date] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
