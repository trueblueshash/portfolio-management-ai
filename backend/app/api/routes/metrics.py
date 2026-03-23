"""
Portfolio metrics API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import os
import shutil
import logging

from app.db.session import get_db
from app.models.company import Company
from app.models.portfolio_metrics import PortfolioMetrics, MetricsCatalog
from app.services.gdrive_service import (
    list_folder_files,
    download_file,
    extract_folder_id,
    categorize_files,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/companies/{company_id}")
def get_company_metrics(
    company_id: UUID,
    period_type: str = Query("monthly"),
    include_projected: bool = Query(True),
    limit: int = Query(24),
    db: Session = Depends(get_db)
):
    """Get metrics time series for a company"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    query = db.query(PortfolioMetrics).filter(
        PortfolioMetrics.company_id == company_id,
        PortfolioMetrics.period_type == period_type,
    )
    if not include_projected:
        query = query.filter(PortfolioMetrics.is_projected == False)

    metrics = query.order_by(PortfolioMetrics.period.desc()).limit(limit).all()

    catalog = db.query(MetricsCatalog).filter(
        MetricsCatalog.company_id == company_id
    ).all()

    catalog_map = {c.raw_name: {
        "display_name": c.display_name,
        "category": c.category,
        "unit": c.unit,
        "is_headline": c.is_headline,
    } for c in catalog}

    return {
        "company_id": str(company_id),
        "company_name": company.name,
        "periods": [
            {
                "period": m.period.isoformat(),
                "period_label": m.period_label,
                "is_projected": m.is_projected,
                "metrics": m.metrics,
                "source": m.source,
                "currency": m.currency or "USD",
            }
            for m in reversed(metrics)
        ],
        "catalog": catalog_map,
    }


@router.get("/companies/{company_id}/headline")
def get_headline_metrics(
    company_id: UUID,
    db: Session = Depends(get_db)
):
    """Get headline KPIs for company overview card"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    latest = db.query(PortfolioMetrics).filter(
        PortfolioMetrics.company_id == company_id,
        PortfolioMetrics.is_projected == False,
    ).order_by(PortfolioMetrics.period.desc()).first()

    if not latest:
        return {"company_name": company.name, "headlines": [], "period": None}

    currency = latest.currency if latest and latest.currency else "USD"

    previous = db.query(PortfolioMetrics).filter(
        PortfolioMetrics.company_id == company_id,
        PortfolioMetrics.is_projected == False,
        PortfolioMetrics.period < latest.period,
    ).order_by(PortfolioMetrics.period.desc()).first()

    headlines = db.query(MetricsCatalog).filter(
        MetricsCatalog.company_id == company_id,
        MetricsCatalog.is_headline == True,
    ).all()

    result = []
    for h in headlines:
        current_val = latest.metrics.get(h.raw_name)
        prev_val = previous.metrics.get(h.raw_name) if previous else None

        change = None
        if current_val is not None and prev_val is not None and prev_val != 0:
            change = round((current_val - prev_val) / abs(prev_val) * 100, 1)

        result.append({
            "name": h.display_name,
            "raw_name": h.raw_name,
            "value": current_val,
            "previous_value": prev_val,
            "change_pct": change,
            "unit": h.unit,
            "category": h.category,
        })

    return {
        "company_name": company.name,
        "period": latest.period_label,
        "period_date": latest.period.isoformat(),
        "currency": currency,
        "headlines": result,
    }


@router.get("/companies/{company_id}/standard-view")
def get_standard_view(
    company_id: UUID,
    limit: int = Query(12),
    db: Session = Depends(get_db)
):
    """
    Adaptive standard view — groups metrics by category, only shows populated data.
    No fixed template; it discovers what data exists and organizes it.
    """
    from app.services.mis_parser import CATEGORY_DISPLAY_ORDER, detect_company_type

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company_type = detect_company_type(company.market_tags or [])

    # Get actual periods with data
    periods = db.query(PortfolioMetrics).filter(
        PortfolioMetrics.company_id == company_id,
        PortfolioMetrics.is_projected == False,
    ).order_by(PortfolioMetrics.period.desc()).limit(limit).all()
    periods = list(reversed(periods))

    if not periods:
        return {"company_name": company.name, "company_type": company_type, "sections": {}}

    # Get catalog
    catalog_entries = db.query(MetricsCatalog).filter(
        MetricsCatalog.company_id == company_id
    ).all()

    # Group catalog entries by category
    category_metrics = {}
    for entry in catalog_entries:
        cat = entry.category
        if cat not in category_metrics:
            category_metrics[cat] = []

        # Check if this metric has ANY data in recent periods
        has_data = False
        for p in periods[-6:]:  # Check last 6 periods
            if entry.raw_name in p.metrics and p.metrics[entry.raw_name] is not None:
                has_data = True
                break

        if has_data:
            category_metrics[cat].append({
                "raw_name": entry.raw_name,
                "display_name": entry.display_name,
                "unit": entry.unit,
                "is_headline": entry.is_headline,
                "values": [
                    {
                        "period": p.period.isoformat(),
                        "period_label": p.period_label,
                        "value": p.metrics.get(entry.raw_name),
                    }
                    for p in periods
                ],
            })

    # Sort categories by preferred order, only include non-empty ones
    ordered_sections = {}
    for cat in CATEGORY_DISPLAY_ORDER:
        if cat in category_metrics and category_metrics[cat]:
            ordered_sections[cat] = category_metrics[cat]

    # Add any remaining categories not in the preferred order
    for cat, metrics in category_metrics.items():
        if cat not in ordered_sections and metrics:
            ordered_sections[cat] = metrics

    return {
        "company_name": company.name,
        "company_type": company_type,
        "latest_period": periods[-1].period_label if periods else None,
        "sections": ordered_sections,
    }


@router.post("/companies/{company_id}/upload-mis")
async def upload_mis(
    company_id: UUID,
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Upload MIS Excel and parse metrics. Re-uploading updates existing periods."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="File must be .xlsx or .xls")

    upload_dir = "uploads/mis"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{company.name.replace(' ', '_')}_{file.filename}")

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        from app.services.mis_parser import parse_mis_excel
        result = parse_mis_excel(file_path, company_id, db, sheet_name=sheet_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing MIS: {str(e)}")


@router.post("/companies/{company_id}/catalog/{metric_name}/headline")
def toggle_headline(
    company_id: UUID,
    metric_name: str,
    is_headline: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Toggle a metric as headline/non-headline for the company summary card"""
    entry = db.query(MetricsCatalog).filter(
        MetricsCatalog.company_id == company_id,
        MetricsCatalog.raw_name == metric_name,
    ).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Metric not found in catalog")

    entry.is_headline = is_headline
    db.commit()
    return {"status": "updated", "metric": metric_name, "is_headline": is_headline}


@router.post("/companies/{company_id}/sync-from-drive")
def sync_from_drive(
    company_id: UUID,
    folder_url: str = Query(..., description="Google Drive folder URL"),
    sheet_name: Optional[str] = Query(None, description="Excel sheet name to parse"),
    db: Session = Depends(get_db)
):
    """
    Scan a Google Drive folder and ingest ALL files for a company:
    - Excel files → MIS metrics parser → portfolio_metrics table
    - Google Docs → existing document pipeline → chunks + embeddings + RAG
    - PDFs → download and store for future processing

    The folder must be shared with the service account.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    try:
        folder_id = extract_folder_id(folder_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # List all files in folder
    try:
        all_files = list_folder_files(folder_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cannot access Drive folder. Share it with portfolio-doc-sync@lightspeed-ai-platform.iam.gserviceaccount.com. Error: {str(e)}"
        )

    if not all_files:
        return {"status": "empty", "message": "No files found in folder"}

    categorized = categorize_files(all_files)
    results = {
        "company": company.name,
        "folder_id": folder_id,
        "files_found": len(all_files),
        "excel_results": [],
        "google_doc_results": [],
        "pdf_results": [],
        "errors": [],
    }

    upload_dir = "uploads/mis"
    os.makedirs(upload_dir, exist_ok=True)

    # 1. Process Excel files → MIS metrics
    for excel_file in categorized["excel"]:
        logger.info(f"Processing Excel: {excel_file['name']}")
        file_name = excel_file['name']
        if not file_name.endswith(('.xlsx', '.xls')):
            file_name = f"{file_name}.xlsx"
        local_path = os.path.join(upload_dir, f"{company.name.replace(' ', '_')}_{file_name}")
        try:
            # Google Sheets need to be exported, regular Excel files are downloaded
            if excel_file.get('mimeType') == 'application/vnd.google-apps.spreadsheet':
                from app.services.gdrive_service import export_google_sheet_as_excel
                export_google_sheet_as_excel(excel_file['id'], local_path)
            else:
                download_file(excel_file['id'], local_path)
            from app.services.mis_parser import parse_mis_excel
            result = parse_mis_excel(local_path, company_id, db, sheet_name=sheet_name)
            result["file_name"] = excel_file["name"]
            results["excel_results"].append(result)
        except Exception as e:
            logger.error(f"Error processing {excel_file['name']}: {e}")
            results["errors"].append({"file": excel_file["name"], "type": "excel", "error": str(e)})

    # 2. Process Google Docs → document pipeline (chunks + embeddings)
    from app.models.document import PortfolioDocument
    from app.utils.document_parser import parse_document_metadata
    from app.services.document_processor import process_document

    for gdoc in categorized["google_doc"]:
        logger.info(f"Processing Google Doc: {gdoc['name']}")
        try:
            doc_id = gdoc["id"]

            # Check if already linked
            existing = db.query(PortfolioDocument).filter(
                PortfolioDocument.google_doc_id == doc_id,
                PortfolioDocument.company_id == company_id
            ).first()

            if existing:
                # Re-sync existing document
                from app.services.gdocs_service import sync_single_google_doc
                sync_result = sync_single_google_doc(existing, db)
                results["google_doc_results"].append({
                    "file_name": gdoc["name"],
                    "status": "re-synced",
                    "chunks_created": sync_result.get("chunks_created", 0),
                })
                continue

            # New document — create and process
            metadata = parse_document_metadata(gdoc["name"])

            document = PortfolioDocument(
                company_id=company_id,
                title=metadata["title"],
                doc_type=metadata["doc_type"],
                document_date=metadata["document_date"],
                file_name=f"{gdoc['name']}.gdoc",
                file_url=f"https://docs.google.com/document/d/{doc_id}/edit",
                mime_type="application/vnd.google-apps.document",
                google_doc_id=doc_id,
                is_primary_source=True,
                requires_processing=True,
                storage_purpose="primary_knowledge",
                is_active=True,
                is_processed=False,
            )
            db.add(document)
            db.commit()
            db.refresh(document)

            # Process: extract text, chunk, embed, summarize
            process_document(str(document.id), db)

            results["google_doc_results"].append({
                "file_name": gdoc["name"],
                "status": "new — processed",
                "document_id": str(document.id),
            })

        except Exception as e:
            logger.error(f"Error processing {gdoc['name']}: {e}")
            results["errors"].append({"file": gdoc["name"], "type": "google_doc", "error": str(e)})

    # 3. Log PDFs found (not processed yet, but noted)
    for pdf_file in categorized["pdf"]:
        results["pdf_results"].append({
            "file_name": pdf_file["name"],
            "status": "found — not processed yet",
            "drive_id": pdf_file["id"],
        })

    return results


@router.get("/drive/folder")
def list_drive_folder(
    folder_url: str = Query(..., description="Google Drive folder URL"),
):
    """List all files in a Google Drive folder for browsing."""
    try:
        folder_id = extract_folder_id(folder_url)
        files = list_folder_files(folder_id)
        categorized = categorize_files(files)
        return {
            "folder_id": folder_id,
            "total_files": len(files),
            "excel_files": [{"name": f["name"], "id": f["id"], "modified": f.get("modifiedTime")} for f in categorized["excel"]],
            "google_docs": [{"name": f["name"], "id": f["id"], "modified": f.get("modifiedTime")} for f in categorized["google_doc"]],
            "pdfs": [{"name": f["name"], "id": f["id"], "modified": f.get("modifiedTime")} for f in categorized["pdf"]],
            "other": [{"name": f["name"], "id": f["id"], "type": f["mimeType"]} for f in categorized["other"]],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
