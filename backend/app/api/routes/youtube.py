from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.youtube_service import (
    get_company_scans,
    scan_all_companies_youtube,
    scan_company_youtube,
)

router = APIRouter(prefix="/youtube", tags=["youtube"])


@router.post("/scan/companies/{company_id}")
async def scan_company(
    company_id: UUID,
    days_back: int = Query(default=14, le=30),
    max_queries: int = Query(default=20, le=50),
    db: Session = Depends(get_db),
):
    """Search YouTube for videos relevant to a specific portfolio company's competitors and market."""
    try:
        stats = await scan_company_youtube(company_id, db, days_back=days_back, max_queries=max_queries)
        return {"status": "ok", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan/all")
async def scan_all(
    days_back: int = Query(default=14, le=30),
    db: Session = Depends(get_db),
):
    """Scan YouTube for all active portfolio companies."""
    try:
        stats = await scan_all_companies_youtube(db, days_back=days_back)
        return {"status": "ok", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scans/companies/{company_id}")
def get_scans(
    company_id: UUID,
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    """Get recent YouTube scan results for a company."""
    return {"status": "ok", "data": get_company_scans(company_id, db, limit=limit)}
