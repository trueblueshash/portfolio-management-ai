from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.comps_service import get_latest_comps, refresh_comps

router = APIRouter(prefix="/comps", tags=["comps"])


@router.get("/companies/{company_id}")
def get_comps(company_id: UUID, db: Session = Depends(get_db)):
    """Get cached comps data for a company."""
    results = get_latest_comps(company_id, db)
    if not results:
        return {"status": "not_generated", "data": []}
    return {"status": "ok", "data": results}


@router.post("/companies/{company_id}/refresh")
def refresh(company_id: UUID, db: Session = Depends(get_db)):
    """Pull fresh comps data from yfinance."""
    try:
        results = refresh_comps(company_id, db)
        return {"status": "ok", "data": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
