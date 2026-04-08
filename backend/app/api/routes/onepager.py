from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.onepager_service import (
    generate_onepager,
    get_latest_onepager,
    update_onepager_field,
)

router = APIRouter(prefix="/onepager", tags=["onepager"])


@router.get("/companies/{company_id}")
def get_onepager(company_id: UUID, db: Session = Depends(get_db)):
    """Get the latest one-pager for a company."""
    result = get_latest_onepager(company_id, db)
    if not result:
        return {"status": "not_generated", "data": None}
    return {"status": "ok", "data": result}


@router.post("/companies/{company_id}/generate")
async def generate(company_id: UUID, db: Session = Depends(get_db)):
    """Generate a new one-pager using AI."""
    try:
        result = await generate_onepager(company_id, db)
        return {"status": "ok", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FieldUpdate(BaseModel):
    field: str
    value: Any


@router.patch("/{onepager_id}")
def update_field(onepager_id: UUID, update: FieldUpdate, db: Session = Depends(get_db)):
    """Update a single field on a one-pager (manual edit)."""
    try:
        result = update_onepager_field(onepager_id, update.field, update.value, db)
        return {"status": "ok", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
