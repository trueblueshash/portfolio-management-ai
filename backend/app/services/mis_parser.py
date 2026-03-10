"""
MIS Excel parser - reads Salesforce tear sheet exports and extracts metrics.
Handles different company types by detecting type from market_tags and applying
the right metric classification patterns.

Supports re-uploads: uses upsert logic so uploading a new MIS for the same company
updates existing periods and adds new ones. Tracks upload_batch to know when data came in.
"""
import logging
import re
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID
import pandas as pd
from sqlalchemy.orm import Session

from app.models.portfolio_metrics import PortfolioMetrics, MetricsCatalog
from app.models.company import Company

logger = logging.getLogger(__name__)


# ── Company Type Detection ─────────────────────────────────────────────────

COMPANY_TYPE_KEYWORDS = {
    "saas": ["saas", "software", "platform", "automation", "cloud", "api", "devops",
             "observability", "compliance", "grc", "hrms", "management", "workflow",
             "b2b", "enterprise", "subscription"],
    "deeptech": ["satellite", "imaging", "space", "drone", "energy", "battery", "ev",
                 "hardware", "genomics", "oncology", "medical", "robotics", "quantum",
                 "biotech", "semiconductor", "sensor"],
    "fintech": ["crypto", "treasury", "banking", "payment", "lending", "insurance",
                "finance", "neobank", "wallet", "exchange", "trading"],
    "consumer": ["creator", "content", "marketplace", "consumer", "social", "influencer",
                 "d2c", "ecommerce", "gaming", "media", "entertainment"],
}


def detect_company_type(market_tags: list) -> str:
    """Detect company type from market tags."""
    if not market_tags:
        return "saas"
    tags_lower = " ".join(t.lower() for t in market_tags)

    scores = {}
    for company_type, keywords in COMPANY_TYPE_KEYWORDS.items():
        scores[company_type] = sum(1 for kw in keywords if kw in tags_lower)

    best_type = max(scores, key=scores.get)
    return best_type if scores[best_type] > 0 else "saas"


# ── Metric Classification Patterns by Company Type ─────────────────────────

METRIC_PATTERNS_BY_TYPE = {
    "saas": {
        "revenue": [r"arr", r"mrr", r"revenue", r"subscription", r"recurring", r"bookings", r"acv", r"net arr"],
        "growth": [r"expansion", r"growth", r"mom.*growth", r"yoy", r"net new", r"new bookings"],
        "retention": [r"churn", r"nrr", r"grr", r"retention", r"logo churn", r"net mrr churn"],
        "unit_economics": [r"ltv", r"cac", r"payback", r"ltv.*cac", r"sales efficiency", r"burn multiple", r"gross margin"],
        "cash": [r"cash", r"burn", r"ebitda", r"capital", r"cash.*balance", r"burn.*rate"],
        "team": [r"employee", r"headcount", r"fte", r"sales.*capacity", r"customer success", r"engineering", r"product", r"sales.*marketing", r"general.*admin"],
        "pipeline": [r"enquir", r"demo", r"win", r"loss", r"pipeline", r"conversion", r"sql", r"poc", r"proposal", r"negotiation"],
        "customers": [r"customer.*end", r"customer.*start", r"new customer", r"number.*customer", r"net new customer"],
    },
    "deeptech": {
        "revenue": [r"revenue", r"arr", r"contract", r"order", r"backlog", r"gmv"],
        "product": [r"satellite", r"launch", r"unit", r"device", r"shipment", r"resolution", r"coverage", r"accuracy", r"mission"],
        "growth": [r"growth", r"expansion", r"new.*contract", r"pipeline"],
        "unit_economics": [r"margin", r"cac", r"ltv", r"payback", r"cost.*per", r"efficiency"],
        "cash": [r"cash", r"burn", r"ebitda", r"runway", r"capital"],
        "team": [r"employee", r"headcount", r"fte", r"engineer", r"scientist"],
        "customers": [r"customer", r"client", r"partner", r"user"],
    },
    "fintech": {
        "revenue": [r"revenue", r"arr", r"net.*interest", r"fee", r"commission", r"take.*rate", r"gmv", r"tpv"],
        "growth": [r"growth", r"expansion", r"volume"],
        "retention": [r"churn", r"retention", r"nrr"],
        "unit_economics": [r"margin", r"cac", r"ltv", r"payback", r"take.*rate", r"spread"],
        "cash": [r"cash", r"burn", r"ebitda", r"working.*capital", r"aum", r"balance.*sheet"],
        "risk": [r"npa", r"default", r"provision", r"loss.*rate", r"risk"],
        "customers": [r"customer", r"user", r"account", r"wallet", r"merchant"],
    },
    "consumer": {
        "revenue": [r"revenue", r"gmv", r"arr", r"take.*rate", r"monetiz"],
        "growth": [r"growth", r"mau", r"dau", r"engagement", r"retention"],
        "unit_economics": [r"margin", r"cac", r"ltv", r"arpu", r"payback"],
        "cash": [r"cash", r"burn", r"ebitda"],
        "users": [r"user", r"creator", r"subscriber", r"download", r"install"],
        "engagement": [r"session", r"time.*spent", r"dau.*mau", r"retention.*d\d"],
    },
}

# Headline metric detection — these are the KPIs that show up in the top summary card
HEADLINE_KEYWORDS = [
    "exit arr", "total mrr actual", "gross margin", "burn multiple",
    "number of customers at end", "monthly nrr", "cash balance",
    "sales efficiency", "burn rate", "ltv to cac",
    # Deeptech
    "satellites", "revenue",
    # Fintech
    "gmv", "tpv", "aum",
    # Consumer
    "mau", "dau", "gmv",
]


def classify_metric(name: str, company_type: str = "saas") -> Tuple[str, str]:
    """Classify a metric name into category and clean display name."""
    name_lower = name.lower().strip()
    patterns = METRIC_PATTERNS_BY_TYPE.get(company_type, METRIC_PATTERNS_BY_TYPE["saas"])

    for category, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, name_lower):
                return category, name.strip()

    return "other", name.strip()


def detect_unit(name: str, values: list) -> str:
    """Detect the unit of a metric from its name and sample values."""
    name_lower = name.lower()

    if "%" in name or "margin" in name_lower or "ratio" in name_lower or "efficiency" in name_lower:
        return "%"
    if "multiple" in name_lower:
        return "x"
    if any(kw in name_lower for kw in ["arr", "mrr", "revenue", "booking", "burn", "cash", "ebitda", "cogs", "cost"]):
        numeric_vals = [v for v in values if isinstance(v, (int, float)) and v != 0]
        if numeric_vals:
            avg = sum(abs(v) for v in numeric_vals) / len(numeric_vals)
            if avg > 1000000:
                return "$"
            elif avg > 1000:
                return "$K"
            else:
                return "$Mn"
        return "$"
    if any(kw in name_lower for kw in ["employee", "fte", "customer", "#", "number", "count"]):
        return "#"
    if "month" in name_lower and "payback" in name_lower:
        return "months"
    if any(kw in name_lower for kw in ["acv", "ltv", "cac"]):
        return "$"

    return ""


def is_headline_metric(name: str) -> bool:
    """Check if a metric should be displayed as a headline KPI."""
    name_lower = name.lower().strip()
    return any(kw in name_lower for kw in HEADLINE_KEYWORDS)


# ── Main Parser ────────────────────────────────────────────────────────────

def parse_mis_excel(
    file_path: str,
    company_id: UUID,
    db: Session,
    sheet_name: str = None
) -> Dict:
    """
    Parse a Salesforce MIS Excel export and store metrics.

    Handles:
    - Auto-detection of company type from market_tags
    - Different Excel structures per company
    - Actuals vs Projected columns
    - Re-uploads: upserts existing periods, adds new ones
    - Upload batch tracking

    Expected structure (Scrut-like):
    - Row 0: Actuals/Planned labels
    - Row 1: Date columns (datetime)
    - Row 2+: Metric rows with name in col 3, values in col 4+

    If sheet_name is None, tries "1. Business Metrics" then falls back to first sheet.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise ValueError(f"Company not found: {company_id}")

    # Detect company type
    company_type = detect_company_type(company.market_tags or [])
    logger.info(f"Parsing MIS for {company.name} (type: {company_type}) from {file_path}")

    # Determine sheet name
    xls = pd.ExcelFile(file_path)
    if sheet_name and sheet_name in xls.sheet_names:
        use_sheet = sheet_name
    elif "1. Business Metrics" in xls.sheet_names:
        use_sheet = "1. Business Metrics"
    else:
        use_sheet = xls.sheet_names[0]

    logger.info(f"Using sheet: {use_sheet}")
    df = pd.read_excel(file_path, sheet_name=use_sheet, header=None)

    # Upload batch ID for tracking
    upload_batch = f"{datetime.now().strftime('%Y%m%d')}_{company.name.lower().replace(' ', '_')}"

    # ── Detect structure ──
    # Find the row with dates (look for datetime values in first 5 rows)
    date_row_idx = None
    label_row_idx = None
    metric_name_col = None
    data_start_col = None

    for row_idx in range(min(5, len(df))):
        for col_idx in range(min(20, len(df.columns))):
            val = df.iloc[row_idx, col_idx]
            if isinstance(val, (datetime, pd.Timestamp)):
                date_row_idx = row_idx
                if date_row_idx > 0:
                    label_row_idx = date_row_idx - 1  # Row above dates has Actuals/Planned
                data_start_col = col_idx
                break
        if date_row_idx is not None:
            break

    if date_row_idx is None:
        raise ValueError("Could not find date row in Excel. Expected datetime values in first 5 rows.")

    # Find metric name column (usually col 3 for Scrut format, or the col just before data_start_col)
    # Look for text values in the column before data starts
    for col_idx in range(data_start_col - 1, -1, -1):
        text_count = sum(1 for r in range(5, min(20, len(df))) if pd.notna(df.iloc[r, col_idx]) and isinstance(df.iloc[r, col_idx], str))
        if text_count >= 3:
            metric_name_col = col_idx
            break

    if metric_name_col is None:
        metric_name_col = data_start_col - 1

    logger.info(f"Structure detected: dates in row {date_row_idx}, labels in row {label_row_idx}, metric names in col {metric_name_col}, data starts col {data_start_col}")

    # ── Extract date columns ──
    dates_row = df.iloc[date_row_idx, data_start_col:]
    labels_row = df.iloc[label_row_idx, data_start_col:] if label_row_idx is not None else pd.Series()

    columns_meta = []
    for i, dt in enumerate(dates_row):
        if pd.notna(dt):
            try:
                if isinstance(dt, (datetime, pd.Timestamp)):
                    period_date = dt.date() if hasattr(dt, "date") else dt
                elif isinstance(dt, date):
                    period_date = dt
                else:
                    continue

                label = labels_row.iloc[i] if i < len(labels_row) else None
                is_projected = False
                if pd.notna(label):
                    is_projected = str(label).strip().lower() in ["planned", "plan", "forecast", "budget", "projected"]

                period_label = period_date.strftime("%b'%y")

                columns_meta.append({
                    "col_index": i + data_start_col,
                    "date": period_date,
                    "label": period_label,
                    "is_projected": is_projected,
                })
            except Exception:
                continue

    logger.info(f"Found {len(columns_meta)} date columns ({columns_meta[0]['label'] if columns_meta else '?'} to {columns_meta[-1]['label'] if columns_meta else '?'})")

    # ── Extract metrics ──
    metrics_by_period = {}
    metric_names = []

    # Skip region sub-rows (these are breakdowns, not top-level metrics)
    skip_names = {"NA/EU", "India/APAC", "US", "EMEA", "APAC", "ROW"}

    for row_idx in range(date_row_idx + 1, len(df)):
        metric_name = df.iloc[row_idx, metric_name_col]
        if pd.isna(metric_name) or not str(metric_name).strip():
            continue

        metric_name = str(metric_name).strip()

        # Skip sub-breakdowns and section headers
        if metric_name in skip_names:
            continue

        values_for_unit = []
        for col_meta in columns_meta:
            val = df.iloc[row_idx, col_meta["col_index"]]
            if pd.notna(val) and isinstance(val, (int, float)):
                values_for_unit.append(val)

            key = (col_meta["date"], col_meta["is_projected"])
            if key not in metrics_by_period:
                metrics_by_period[key] = {}

            if pd.notna(val):
                if isinstance(val, (int, float)):
                    metrics_by_period[key][metric_name] = round(float(val), 2)
                elif isinstance(val, str) and val.strip() not in ["-", "", "nan", "NaN"]:
                    try:
                        metrics_by_period[key][metric_name] = round(float(val.replace(",", "")), 2)
                    except ValueError:
                        pass

        # Add to catalog if new
        if metric_name not in metric_names:
            metric_names.append(metric_name)

            category, display_name = classify_metric(metric_name, company_type)
            unit = detect_unit(metric_name, values_for_unit)
            headline = is_headline_metric(metric_name)

            existing_catalog = db.query(MetricsCatalog).filter(
                MetricsCatalog.company_id == company_id,
                MetricsCatalog.raw_name == metric_name
            ).first()

            if not existing_catalog:
                catalog_entry = MetricsCatalog(
                    company_id=company_id,
                    raw_name=metric_name,
                    display_name=display_name,
                    category=category,
                    unit=unit,
                    is_headline=headline,
                )
                db.add(catalog_entry)
            else:
                # Update category/unit if re-uploading
                existing_catalog.category = category
                existing_catalog.unit = unit

    # ── Store metrics (upsert) ──
    periods_stored = 0
    periods_updated = 0

    for (period_date, is_projected), metrics_dict in metrics_by_period.items():
        if not metrics_dict:
            continue

        period_label = period_date.strftime("%b'%y")

        existing = db.query(PortfolioMetrics).filter(
            PortfolioMetrics.company_id == company_id,
            PortfolioMetrics.period == period_date,
            PortfolioMetrics.period_type == "monthly",
            PortfolioMetrics.is_projected == is_projected,
        ).first()

        if existing:
            existing.metrics = metrics_dict
            existing.upload_batch = upload_batch
            existing.source_file = file_path.split("/")[-1]
            periods_updated += 1
        else:
            pm = PortfolioMetrics(
                company_id=company_id,
                period=period_date,
                period_label=period_label,
                period_type="monthly",
                is_projected=is_projected,
                metrics=metrics_dict,
                source="salesforce_mis",
                source_file=file_path.split("/")[-1],
                upload_batch=upload_batch,
            )
            db.add(pm)
            periods_stored += 1

    db.commit()

    # ── Build result summary ──
    category_counts = {}
    for name in metric_names:
        cat, _ = classify_metric(name, company_type)
        category_counts.setdefault(cat, 0)
        category_counts[cat] += 1

    result = {
        "company": company.name,
        "company_type": company_type,
        "sheet_used": use_sheet,
        "metrics_found": len(metric_names),
        "periods_new": periods_stored,
        "periods_updated": periods_updated,
        "date_range": f"{columns_meta[0]['label']} to {columns_meta[-1]['label']}" if columns_meta else "none",
        "metric_categories": category_counts,
        "upload_batch": upload_batch,
    }

    logger.info(f"✅ Parsed {len(metric_names)} metrics across {periods_stored + periods_updated} periods for {company.name} ({periods_stored} new, {periods_updated} updated)")
    return result
