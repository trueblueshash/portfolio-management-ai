"""
Document upload and management API endpoints.
"""
import os
import uuid
import json
import logging
from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.db.session import get_db
from app.models.document import PortfolioDocument, DocumentChunk
from app.models.company import Company
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentSearchRequest,
    DocumentSearchResult,
    DocumentQuestionRequest,
    DocumentQuestionResponse,
    DocumentCitation,
    DocumentMetadataUpdate,
    DocumentType
)
from app.services.document_processor import process_document_background
# from app.core.celery_app import process_document_task  # Using BackgroundTasks instead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# Create uploads directory if it doesn't exist
UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    company_id: Optional[str] = Form(None),
    title: str = Form(...),
    doc_type: str = Form(...),
    document_date: str = Form(...),
    tags: str = Form("[]"),
    notes: Optional[str] = Form(None),
    uploaded_by: Optional[str] = Form(None),
    storage_purpose: str = Form("reference"),  # 'reference', 'archive', 'primary_knowledge'
    db: Session = Depends(get_db)
):
    """
    Upload document with metadata.
    
    Process:
    1. Validate file type (PDF, DOCX, PPTX only)
    2. Save file to uploads/ directory
    3. Create PortfolioDocument record with metadata
    4. Trigger background processing (Celery task)
    5. Return document ID and status
    """
    # Validate file type
    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ]
    
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, PPTX files allowed")
    
    # Validate doc_type
    try:
        doc_type_enum = DocumentType(doc_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid doc_type. Must be one of: {[e.value for e in DocumentType]}")
    
    # Parse company_id
    company_uuid = None
    if company_id:
        try:
            company_uuid = uuid.UUID(company_id)
            # Verify company exists
            company = db.query(Company).filter(Company.id == company_uuid).first()
            if not company:
                raise HTTPException(status_code=404, detail="Company not found")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid company_id format")
    
    # Parse document_date
    try:
        doc_date = date.fromisoformat(document_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document_date format. Use YYYY-MM-DD")
    
    # Parse tags
    try:
        tags_list = json.loads(tags) if tags else []
        if not isinstance(tags_list, list):
            tags_list = []
    except json.JSONDecodeError:
        tags_list = []
    
    # Save file
    file_extension = os.path.splitext(file.filename)[1]
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOADS_DIR, f"{file_id}{file_extension}")
    
    try:
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Write to disk
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Determine if processing is required
        requires_processing = storage_purpose != "archive"
        is_primary_source = storage_purpose == "primary_knowledge"
        
        # Create document record
        document = PortfolioDocument(
            company_id=company_uuid,
            title=title,
            doc_type=doc_type_enum.value,
            document_date=doc_date,
            file_path=file_path,
            file_name=file.filename,
            file_size_bytes=file_size,
            mime_type=file.content_type,
            tags=tags_list,
            notes=notes,
            is_processed=False,
            uploaded_by=uploaded_by,
            is_primary_source=is_primary_source,
            requires_processing=requires_processing,
            storage_purpose=storage_purpose
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Queue processing in background (only if required)
        if requires_processing:
            background_tasks.add_task(process_document_background, str(document.id))
            logger.info(f"Document processing started in background for {document.id}")
        else:
            logger.info(f"Document {document.id} uploaded as {storage_purpose} - no processing needed")
        
        # Build response
        company_name = document.company.name if document.company else None
        processing_status = "processing" if not document.is_processed else "processed"
        
        return DocumentResponse(
            **{k: v for k, v in document.__dict__.items() if not k.startswith("_")},
            company_name=company_name,
            processing_status=processing_status
        )
        
    except Exception as e:
        # Clean up file if document creation failed
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")


@router.get("", response_model=DocumentListResponse)
def list_documents(
    company_id: Optional[str] = None,
    doc_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List all documents with optional filters"""
    query = db.query(PortfolioDocument)
    
    # Apply filters
    if company_id:
        try:
            company_uuid = uuid.UUID(company_id)
            query = query.filter(PortfolioDocument.company_id == company_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid company_id format")
    
    if doc_type:
        query = query.filter(PortfolioDocument.doc_type == doc_type)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    documents = query.order_by(PortfolioDocument.document_date.desc()).offset(offset).limit(limit).all()
    
    # Build response
    doc_responses = []
    for doc in documents:
        company_name = doc.company.name if doc.company else None
        processing_status = "processed" if doc.is_processed else "processing"
        
        doc_responses.append(DocumentResponse(
            **{k: v for k, v in doc.__dict__.items() if not k.startswith("_")},
            company_name=company_name,
            processing_status=processing_status
        ))
    
    return DocumentListResponse(documents=doc_responses, total=total)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, db: Session = Depends(get_db)):
    """Get a single document by ID"""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document_id format")
    
    document = db.query(PortfolioDocument).filter(PortfolioDocument.id == doc_uuid).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    company_name = document.company.name if document.company else None
    processing_status = "processed" if document.is_processed else "processing"
    
    return DocumentResponse(
        **{k: v for k, v in document.__dict__.items() if not k.startswith("_")},
        company_name=company_name,
        processing_status=processing_status
    )


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    """Delete a document and its file"""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document_id format")
    
    document = db.query(PortfolioDocument).filter(PortfolioDocument.id == doc_uuid).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file
    if os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
        except Exception as e:
            logger.warning(f"Could not delete file {document.file_path}: {e}")
    
    # Delete document (chunks will be cascade deleted)
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully"}


@router.post("/search", response_model=List[DocumentSearchResult])
def search_documents(
    request: DocumentSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Semantic search across documents using embeddings.
    Note: This is a simplified version. For production, use pgvector with proper vector similarity search.
    """
    # For now, return a simple text search
    # TODO: Implement proper vector similarity search with pgvector
    
    query = db.query(PortfolioDocument).filter(PortfolioDocument.is_processed == True)
    
    if request.company_id:
        query = query.filter(PortfolioDocument.company_id == request.company_id)
    
    if request.doc_type:
        query = query.filter(PortfolioDocument.doc_type == request.doc_type)
    
    documents = query.all()
    
    results = []
    for doc in documents:
        # Simple text matching for now
        if request.query.lower() in (doc.full_text or "").lower() or request.query.lower() in doc.title.lower():
            # Find matching chunks
            chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id,
                DocumentChunk.chunk_text.ilike(f"%{request.query}%")
            ).limit(3).all()
            
            for chunk in chunks:
                results.append(DocumentSearchResult(
                    chunk_text=chunk.chunk_text[:500] + "..." if len(chunk.chunk_text) > 500 else chunk.chunk_text,
                    document_title=doc.title,
                    company_name=doc.company.name if doc.company else None,
                    page_number=chunk.page_number,
                    similarity_score=0.8,  # Placeholder
                    document_id=doc.id
                ))
    
    return results[:request.limit]


@router.post("/ask", response_model=DocumentQuestionResponse)
def ask_question(
    request: DocumentQuestionRequest,
    db: Session = Depends(get_db)
):
    """
    Ask a question about documents using hybrid RAG search.
    
    Uses intelligent prioritization:
    1. Primary Google Docs (is_primary_source=True) - Most recent sections
    2. Reference uploads (if no good matches in primary)
    3. Archived documents (last resort)
    """
    from app.services.rag_search import answer_question_hybrid
    
    # Use hybrid RAG search
    result = answer_question_hybrid(
        question=request.question,
        company_id=request.company_id,
        search_scope=request.search_scope,
        db=db
    )
    
    # Convert sources to DocumentCitation format
    citations = []
    for source in result.get("sources", []):
        citations.append(DocumentCitation(
            document_title=source.get("document_title", ""),
            company_name=source.get("company_name"),
            page_number=None,  # Google Docs don't have page numbers
            chunk_text=source.get("chunk_text", "")
        ))
    
    return DocumentQuestionResponse(
        answer=result.get("answer", "No answer generated."),
        sources=citations,
        confidence=result.get("confidence", 0.0)
    )


@router.patch("/{document_id}", response_model=DocumentResponse)
def update_document_metadata(
    document_id: str,
    update: DocumentMetadataUpdate,
    db: Session = Depends(get_db)
):
    """Update document metadata"""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document_id format")
    
    document = db.query(PortfolioDocument).filter(PortfolioDocument.id == doc_uuid).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update fields
    if update.title is not None:
        document.title = update.title
    if update.doc_type is not None:
        document.doc_type = update.doc_type.value
    if update.document_date is not None:
        document.document_date = update.document_date
    if update.tags is not None:
        document.tags = update.tags
    if update.notes is not None:
        document.notes = update.notes
    
    db.commit()
    db.refresh(document)
    
    company_name = document.company.name if document.company else None
    processing_status = "processed" if document.is_processed else "processing"
    
    return DocumentResponse(
        **{k: v for k, v in document.__dict__.items() if not k.startswith("_")},
        company_name=company_name,
        processing_status=processing_status
    )

