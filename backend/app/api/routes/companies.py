from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
from app.db.session import get_db
from app.models.company import Company
from app.models.intelligence import IntelligenceItem
from app.schemas.company import Company as CompanySchema, CompanyCreate, CompanyWithStats
from app.core.celery_app import scrape_company
from app.services.gdocs_service import extract_google_doc_id, sync_company_google_doc, extract_google_doc_content
from app.models.document import PortfolioDocument, DocumentChunk
from app.utils.document_parser import parse_document_metadata
from app.services.document_processor import process_document
from fastapi import BackgroundTasks
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=List[CompanyWithStats])
def list_companies(db: Session = Depends(get_db)):
    """List all companies with stats (unread count, total items, last update)"""
    companies = db.query(Company).all()
    
    result = []
    for company in companies:
        # Get unread count
        unread_count = db.query(func.count(IntelligenceItem.id)).filter(
            IntelligenceItem.company_id == company.id,
            IntelligenceItem.is_read == False
        ).scalar() or 0
        
        # Get total items count
        total_items = db.query(func.count(IntelligenceItem.id)).filter(
            IntelligenceItem.company_id == company.id
        ).scalar() or 0
        
        # Get last update (most recent published_date)
        last_update = db.query(func.max(IntelligenceItem.published_date)).filter(
            IntelligenceItem.company_id == company.id
        ).scalar()
        
        company_dict = {
            **CompanySchema.model_validate(company).model_dump(),
            "unread_count": unread_count,
            "total_items": total_items,
            "last_update": last_update,
        }
        result.append(CompanyWithStats(**company_dict))
    
    return result


@router.get("/{company_id}", response_model=CompanyWithStats)
def get_company(company_id: UUID, db: Session = Depends(get_db)):
    """Get single company with detailed stats"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get stats
    unread_count = db.query(func.count(IntelligenceItem.id)).filter(
        IntelligenceItem.company_id == company.id,
        IntelligenceItem.is_read == False
    ).scalar() or 0
    
    total_items = db.query(func.count(IntelligenceItem.id)).filter(
        IntelligenceItem.company_id == company.id
    ).scalar() or 0
    
    last_update = db.query(func.max(IntelligenceItem.published_date)).filter(
        IntelligenceItem.company_id == company.id
    ).scalar()
    
    company_dict = {
        **CompanySchema.model_validate(company).model_dump(),
        "unread_count": unread_count,
        "total_items": total_items,
        "last_update": last_update,
    }
    return CompanyWithStats(**company_dict)


@router.post("", response_model=CompanySchema, status_code=201)
def create_company(company: CompanyCreate, db: Session = Depends(get_db)):
    """Create new company"""
    db_company = Company(**company.model_dump())
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company


@router.post("/{company_id}/scrape")
def trigger_scrape(company_id: UUID, db: Session = Depends(get_db)):
    """Trigger manual scrape for a company"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Trigger Celery task
    task = scrape_company.delay(str(company_id))
    return {"task_id": task.id, "message": "Scrape task started"}


# Google Doc endpoints
class ConnectGoogleDocRequest(BaseModel):
    google_doc_url: str
    sync_enabled: bool = True
    sync_frequency_minutes: int = 60


@router.post("/{company_id}/connect-gdoc")
def connect_google_doc(
    company_id: UUID,
    request: ConnectGoogleDocRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Connect a Google Doc to a company (legacy endpoint - now uses add_company_document).
    This endpoint is kept for backward compatibility but now creates a PortfolioDocument
    instead of setting primary_gdoc_id.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        # Use the new add_company_document endpoint logic
        from app.utils.document_parser import parse_document_metadata
        
        doc_id = extract_google_doc_id(request.google_doc_url)
        
        # Check if document already exists
        existing = db.query(PortfolioDocument).filter(
            PortfolioDocument.google_doc_id == doc_id,
            PortfolioDocument.company_id == company_id
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="This Google Doc is already linked to this company")
        
        # Fetch document title from Google Docs API
        title = None
        try:
            from app.services.gdocs_service import get_google_docs_service
            service = get_google_docs_service()
            doc = service.documents().get(documentId=doc_id).execute()
            title = doc.get('title', f"{company.name} Document")
        except Exception as e:
            logger.warning(f"Could not fetch document title: {e}")
            title = f"{company.name} Document"
        
        # Parse metadata from title
        metadata = parse_document_metadata(title)
        
        # Create PortfolioDocument record
        document = PortfolioDocument(
            company_id=company_id,
            title=metadata["title"],
            doc_type=metadata["doc_type"],
            document_date=metadata["document_date"],
            file_name=f"{title}.gdoc",
            file_url=request.google_doc_url,
            mime_type="application/vnd.google-apps.document",
            google_doc_id=doc_id,
            is_primary_source=True,  # All Google Docs are primary sources
            requires_processing=True,
            storage_purpose="primary_knowledge",
            is_active=True,
            is_processed=False
        )
        
        db.add(document)
        
        # Update company sync settings (but not primary_gdoc_id)
        company.gdoc_sync_enabled = request.sync_enabled
        company.gdoc_sync_frequency_minutes = request.sync_frequency_minutes
        
        db.commit()
        db.refresh(document)
        
        # Trigger processing in background
        from app.services.document_processor import process_document
        background_tasks.add_task(process_document, str(document.id), db)
        
        return {
            "status": "connected",
            "doc_id": doc_id,
            "document_id": str(document.id),
            "message": "Google Doc connected and processing started"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error connecting Google Doc: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error connecting Google Doc: {str(e)}")


@router.post("/{company_id}/sync-gdoc")
def sync_google_doc(company_id: UUID, db: Session = Depends(get_db)):
    """Manually trigger Google Doc sync for all active documents"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check for active Google Docs (not using primary_gdoc_id anymore)
    active_docs = db.query(PortfolioDocument).filter(
        PortfolioDocument.company_id == company_id,
        PortfolioDocument.google_doc_id.isnot(None),
        PortfolioDocument.is_active == True
    ).count()
    
    if active_docs == 0:
        raise HTTPException(status_code=400, detail="No active Google Docs connected to this company")
    
    try:
        sync_result = sync_company_google_doc(company_id, db)
        return sync_result
    except Exception as e:
        logger.error(f"Error syncing Google Doc: {e}")
        raise HTTPException(status_code=500, detail=f"Error syncing Google Doc: {str(e)}")


@router.get("/{company_id}/gdoc-status")
def get_google_doc_status(company_id: UUID, db: Session = Depends(get_db)):
    """Get Google Doc sync status for a company"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check for active Google Docs (not using primary_gdoc_id anymore)
    documents = db.query(PortfolioDocument).filter(
        PortfolioDocument.company_id == company_id,
        PortfolioDocument.google_doc_id.isnot(None),
        PortfolioDocument.is_active == True
    ).all()
    
    if not documents:
        return {
            "connected": False,
            "message": "No Google Docs connected",
            "document_count": 0
        }
    
    # Calculate next sync time
    next_sync = None
    if company.gdoc_last_synced and company.gdoc_sync_enabled:
        from datetime import timedelta
        next_sync = company.gdoc_last_synced + timedelta(minutes=company.gdoc_sync_frequency_minutes)
    
    # Get latest document by date
    latest_doc = max(documents, key=lambda d: d.document_date) if documents else None
    
    return {
        "connected": True,
        "document_count": len(documents),
        "latest_doc_id": latest_doc.google_doc_id if latest_doc else None,
        "latest_doc_url": latest_doc.file_url if latest_doc else None,
        "sync_enabled": company.gdoc_sync_enabled,
        "last_synced": company.gdoc_last_synced,
        "next_sync": next_sync,
        "sync_frequency_minutes": company.gdoc_sync_frequency_minutes
    }


# Multiple documents endpoints
class AddDocumentRequest(BaseModel):
    gdoc_url: str
    title: Optional[str] = None  # If not provided, will fetch from Google Doc


class DocumentResponse(BaseModel):
    id: str
    title: str
    document_date: str
    doc_type: str
    is_processed: bool
    is_active: bool
    google_doc_id: Optional[str]
    file_url: Optional[str]
    created_at: str
    updated_at: str
    summary: Optional[str] = None


@router.post("/{company_id}/documents", response_model=DocumentResponse, status_code=201)
def add_company_document(
    company_id: UUID,
    request: AddDocumentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Add a new Google Doc to a company"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        # Extract doc ID from URL
        doc_id = extract_google_doc_id(request.gdoc_url)
        
        # Check if document already exists
        existing = db.query(PortfolioDocument).filter(
            PortfolioDocument.google_doc_id == doc_id,
            PortfolioDocument.company_id == company_id
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="This Google Doc is already linked to this company")
        
        # Fetch document title from Google Docs API if not provided
        title = request.title
        if not title:
            try:
                from app.services.gdocs_service import get_google_docs_service
                service = get_google_docs_service()
                doc = service.documents().get(documentId=doc_id).execute()
                title = doc.get('title', f"{company.name} Document")
            except Exception as e:
                logger.warning(f"Could not fetch document title: {e}")
                title = f"{company.name} Document"
        
        # Parse metadata from title
        metadata = parse_document_metadata(title)
        
        # Create PortfolioDocument record
        document = PortfolioDocument(
            company_id=company_id,
            title=metadata["title"],
            doc_type=metadata["doc_type"],
            document_date=metadata["document_date"],
            file_name=f"{title}.gdoc",
            file_url=request.gdoc_url,
            mime_type="application/vnd.google-apps.document",
            google_doc_id=doc_id,
            is_primary_source=True,  # All Google Docs are primary sources
            requires_processing=True,
            storage_purpose="primary_knowledge",
            is_active=True,
            is_processed=False
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Trigger processing in background
        background_tasks.add_task(process_document, str(document.id), db)
        
        return DocumentResponse(
            id=str(document.id),
            title=document.title,
            document_date=document.document_date.isoformat(),
            doc_type=document.doc_type,
            is_processed=document.is_processed,
            is_active=document.is_active,
            google_doc_id=document.google_doc_id,
            file_url=document.file_url,
            created_at=document.created_at.isoformat(),
            updated_at=document.updated_at.isoformat(),
            summary=document.summary
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding document: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error adding document: {str(e)}")


@router.get("/{company_id}/documents", response_model=List[DocumentResponse])
def list_company_documents(company_id: UUID, db: Session = Depends(get_db)):
    """List all Google Docs linked to a company, ordered by document_date (latest first)"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get all Google Docs, ordered by document_date descending (latest first)
    documents = db.query(PortfolioDocument).filter(
        PortfolioDocument.company_id == company_id,
        PortfolioDocument.google_doc_id.isnot(None)
    ).order_by(PortfolioDocument.document_date.desc(), PortfolioDocument.created_at.desc()).all()
    
    return [
        DocumentResponse(
            id=str(doc.id),
            title=doc.title,
            document_date=doc.document_date.isoformat(),
            doc_type=doc.doc_type,
            is_processed=doc.is_processed,
            is_active=doc.is_active,
            google_doc_id=doc.google_doc_id,
            file_url=doc.file_url,
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat(),
            summary=doc.summary
        )
        for doc in documents
    ]


@router.delete("/{company_id}/documents/{document_id}")
def delete_company_document(
    company_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db)
):
    """Remove a Google Doc from a company (also deletes associated chunks)"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    document = db.query(PortfolioDocument).filter(
        PortfolioDocument.id == document_id,
        PortfolioDocument.company_id == company_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete associated chunks (cascade should handle this, but being explicit)
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    
    # Delete document
    db.delete(document)
    db.commit()
    
    return {"status": "deleted", "message": f"Document {document.title} removed successfully"}

