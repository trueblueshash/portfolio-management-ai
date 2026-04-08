from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.db.session import get_db
from app.models.intelligence import IntelligenceItem
from app.models.company import Company
from app.services.dedup_helper import is_duplicate_title
from app.schemas.intelligence import IntelligenceItem as IntelligenceItemSchema, IntelligenceItemCreate, IntelligenceItemUpdate

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.get("/companies/{company_id}/intelligence", response_model=List[IntelligenceItemSchema])
def get_company_intelligence(
    company_id: UUID,
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    category: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get intelligence feed for a company with filters"""
    # Verify company exists
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Build query
    query = db.query(IntelligenceItem).filter(IntelligenceItem.company_id == company_id)
    
    # Apply filters
    if date_from:
        query = query.filter(IntelligenceItem.published_date >= date_from)
    if date_to:
        query = query.filter(IntelligenceItem.published_date <= date_to)
    if category:
        query = query.filter(IntelligenceItem.result_category == category)
    if source_type:
        query = query.filter(IntelligenceItem.source_type == source_type)
    if is_read is not None:
        query = query.filter(IntelligenceItem.is_read == is_read)
    
    # Order by published_date DESC, then by captured_date DESC
    query = query.order_by(
        IntelligenceItem.published_date.desc().nullslast(),
        IntelligenceItem.captured_date.desc()
    )
    
    # Apply pagination
    items = query.offset(offset).limit(limit).all()
    return items


@router.post("", response_model=IntelligenceItemSchema, status_code=201)
def create_intelligence_item(item: IntelligenceItemCreate, db: Session = Depends(get_db)):
    """Manually create intelligence item"""
    # Verify company exists
    company = db.query(Company).filter(Company.id == item.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check for duplicate source_url
    existing = db.query(IntelligenceItem).filter(
        IntelligenceItem.source_url == item.source_url
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Intelligence item with this source_url already exists")

    if is_duplicate_title(db, item.company_id, item.title):
        raise HTTPException(status_code=400, detail="Intelligence item with similar title already exists recently")
    
    db_item = IntelligenceItem(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/{item_id}/read")
def mark_as_read(item_id: UUID, update: IntelligenceItemUpdate, db: Session = Depends(get_db)):
    """Mark intelligence item as read/unread"""
    item = db.query(IntelligenceItem).filter(IntelligenceItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Intelligence item not found")
    
    if update.is_read is not None:
        item.is_read = update.is_read
        db.commit()
        db.refresh(item)
    
    return {"id": item.id, "is_read": item.is_read}

