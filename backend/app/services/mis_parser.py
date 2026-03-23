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

# Skip regional breakdown rows and known sub-labels entirely
SKIP_METRIC_NAMES = {
    "NA/EU", "India/APAC", "US", "EMEA", "APAC", "ROW", "India", "NA", "EU",
    "US-C1", "US-C2+C3", "US C1", "US C2+C3", "Powai", "Sarjapur",
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


# Preferred display order for metric categories in the standard view
# Categories not in this list appear at the end
CATEGORY_DISPLAY_ORDER = [
    "revenue", "growth", "retention", "unit_economics",
    "cash", "customers", "pipeline", "team", "other"
]


def _is_sub_breakdown_row(df, row_idx: int, metric_name_col: int, data_start_col: int) -> bool:
    """
    Detect if a row is a sub-breakdown that should be skipped.
    Uses STRUCTURAL signals, not hardcoded names:

    1. Check if the row's col 0 contains concatenated parent+child text
       (Sheet 2 pattern: "Cost of Goods Sold (COGS)Server Hosting charges")
    2. Check if the row has no value in col 2 (cumulative column) while the
       row above it does — indicates this is a sub-row under a total
    3. Check if the metric name is identical to a known regional pattern
       but ONLY as a fallback
    """
    name = df.iloc[row_idx, metric_name_col]
    if pd.isna(name):
        return True  # Empty row, skip

    name_str = str(name).strip()
    if not name_str:
        return True

    # Signal 1: Col 0 has concatenated parent+child text (Sheet 2 pattern)
    # e.g., "Cost of Goods Sold (COGS)Server Hosting charges - Direct expenses"
    # These rows have long text in col 0 that CONTAINS the metric name
    col0 = df.iloc[row_idx, 0]
    if pd.notna(col0):
        col0_str = str(col0).strip()
        # If col 0 has text AND it's longer than the metric name AND contains it,
        # this is a sub-detail row
        if (col0_str and len(col0_str) > len(name_str) + 3
            and name_str in col0_str and col0_str != name_str):
            return True

    # Signal 2: Look at the cumulative column (col 2 in Sheet 1)
    # Total rows typically have a value in col 2; sub-rows don't
    # But only apply this for Sheet 1 style layouts where col 2 has cumulative values
    if metric_name_col == 3 and data_start_col >= 4:
        # Sheet 1 layout: metric name in col 3, check col 2 for cumulative
        col2_val = df.iloc[row_idx, 2]
        has_cumulative = pd.notna(col2_val) and isinstance(col2_val, (int, float))

        # If this row has NO cumulative but the previous named row DID,
        # this is likely a sub-breakdown
        if not has_cumulative:
            # Look back to find the previous row with a metric name
            for prev_idx in range(row_idx - 1, max(row_idx - 4, 0), -1):
                prev_name = df.iloc[prev_idx, metric_name_col]
                if pd.notna(prev_name) and str(prev_name).strip():
                    prev_col2 = df.iloc[prev_idx, 2]
                    if pd.notna(prev_col2) and isinstance(prev_col2, (int, float)):
                        # Previous row had cumulative, this one doesn't → sub-row
                        return True
                    break  # Previous row also had no cumulative, so pattern doesn't apply

    return False


def _parse_single_sheet(
    df,
    company_id,
    company_type: str,
    date_row_idx: int,
    label_row_idx,
    metric_name_col: int,
    data_start_col: int,
    db,
    upload_batch: str,
    source_file: str,
    sheet_label: str = "",
) -> tuple:
    """
    Parse a single sheet. Returns (metrics_by_period, metric_names, columns_meta).
    """
    dates_row = df.iloc[date_row_idx, data_start_col:]
    labels_row = df.iloc[label_row_idx, data_start_col:] if label_row_idx is not None else pd.Series()

    columns_meta = []
    for i, dt in enumerate(dates_row):
        if pd.notna(dt):
            try:
                if isinstance(dt, (datetime, pd.Timestamp)):
                    period_date = dt.date() if hasattr(dt, 'date') else dt
                elif isinstance(dt, date):
                    period_date = dt
                else:
                    continue

                label = labels_row.iloc[i] if i < len(labels_row) else None
                is_projected = False
                if pd.notna(label):
                    label_str = str(label).strip().lower()
                    # Check if this column is projected/planned (not actuals)
                    is_projected = any(kw in label_str for kw in ["plan", "forecast", "budget", "project", "estimate", "target"])
                    # Explicitly NOT projected if labeled as actual
                    if any(kw in label_str for kw in ["actual", "audited", "reported"]):
                        is_projected = False

                period_label = period_date.strftime("%b'%y")
                columns_meta.append({
                    "col_index": i + data_start_col,
                    "date": period_date,
                    "label": period_label,
                    "is_projected": is_projected,
                })
            except Exception:
                continue

    metrics_by_period = {}
    metric_names = []

    for row_idx in range(date_row_idx + 1, len(df)):
        metric_name = df.iloc[row_idx, metric_name_col]
        if pd.isna(metric_name) or not str(metric_name).strip():
            continue

        metric_name = str(metric_name).strip()

        # Skip regional breakdowns and known sub-labels entirely
        if metric_name in SKIP_METRIC_NAMES:
            continue

        # Structural sub-row detection
        if _is_sub_breakdown_row(df, row_idx, metric_name_col, data_start_col):
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

        if metric_name not in metric_names:
            metric_names.append(metric_name)

            from app.models.portfolio_metrics import MetricsCatalog
            category, display = classify_metric(metric_name, company_type)
            unit = detect_unit(metric_name, values_for_unit)
            headline = is_headline_metric(metric_name)

            try:
                existing_catalog = db.query(MetricsCatalog).filter(
                    MetricsCatalog.company_id == company_id,
                    MetricsCatalog.raw_name == metric_name
                ).first()

                if not existing_catalog:
                    catalog_entry = MetricsCatalog(
                        company_id=company_id,
                        raw_name=metric_name,
                        display_name=display,
                        category=category,
                        unit=unit,
                        is_headline=headline,
                    )
                    db.add(catalog_entry)
                    db.flush()
                else:
                    existing_catalog.category = category
                    existing_catalog.unit = unit
            except Exception as catalog_err:
                logger.warning(f"Catalog entry error for {metric_name}: {catalog_err}")
                db.rollback()

    return metrics_by_period, metric_names, columns_meta


def select_headline_metrics_with_ai(
    company_name: str,
    company_type: str,
    metric_names: list,
    db,
    company_id,
    currency: str = "USD",
):
    """
    Use AI to select the 6 most important headline metrics for a company.
    These are the KPIs that show at the top of the company page.
    """
    import json
    from app.services.relevance_filter import client
    from app.models.portfolio_metrics import MetricsCatalog

    if not metric_names:
        return

    metrics_list = "\n".join([f"- {name}" for name in metric_names])

    prompt = f"""You are a senior VC analyst selecting the 6 most important headline KPIs for a portfolio company dashboard.

Company: {company_name}
Company type: {company_type}
Reporting currency: {currency}

Here are ALL available metrics from their MIS:
{metrics_list}

Select EXACTLY 6 metrics that a General Partner would want to see at a glance on the company overview page. These should be:
- The most strategic, high-level metrics (not sub-breakdowns or line items)
- Covering different aspects: revenue/scale, profitability/margins, efficiency, growth, customers/users, and cash
- For SaaS: think ARR, Gross Margin, Burn Multiple, NRR, Customer Count, Cash/Burn
- For Consumer: think GMV/Revenue, Gross Margin, EBITDA, User Growth, Unit Economics, Cash
- For Fintech: think AUM/Revenue, Margins, Burn, User Growth, Key Volume Metric, Cash

Return ONLY a JSON array of exactly 6 metric names, matching the exact names from the list above. No explanation, no markdown, just the JSON array.

Example: ["Exit ARR", "Gross Margin", "Burn Multiple", "Number of Customers at End of Month", "Monthly NRR", "Burn Rate"]"""

    try:
        response = client.chat.completions.create(
            model="anthropic/claude-3.5-haiku",
            messages=[
                {"role": "system", "content": "Return only valid JSON. No markdown, no explanation."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.1,
        )

        result_text = response.choices[0].message.content.strip()
        # Clean up markdown if present
        import re
        result_text = re.sub(r'```json\s*', '', result_text)
        result_text = re.sub(r'```\s*', '', result_text)
        result_text = result_text.strip()

        selected = json.loads(result_text)

        if not isinstance(selected, list) or len(selected) == 0:
            logger.warning(f"AI returned invalid headline selection: {result_text}")
            return

        # Clear all existing headlines for this company
        db.query(MetricsCatalog).filter(
            MetricsCatalog.company_id == company_id
        ).update({'is_headline': False})

        # Set the AI-selected ones
        for name in selected[:6]:
            entry = db.query(MetricsCatalog).filter(
                MetricsCatalog.company_id == company_id,
                MetricsCatalog.raw_name == name
            ).first()
            if entry:
                entry.is_headline = True
                logger.info(f"  📌 Headline: {name}")
            else:
                logger.warning(f"  ⚠️ AI selected '{name}' but not found in catalog")

        db.flush()
        logger.info(f"✅ AI selected {len(selected)} headline metrics for {company_name}")

    except Exception as e:
        logger.error(f"Error in AI headline selection: {e}")
        # Don't fail the whole parse — just skip headline selection


def detect_currency(df, sheet_names: list, file_path: str) -> str:
    """
    Detect currency from the Excel file by scanning headers, sheet names,
    and metric names for currency indicators.
    Returns: "INR", "USD", or "USD" as default
    """
    search_text = ""

    # Collect text from first few rows of each sheet
    for sn in sheet_names[:3]:
        try:
            sheet_df = pd.read_excel(file_path, sheet_name=sn, header=None)
            for i in range(min(10, len(sheet_df))):
                for j in range(min(10, len(sheet_df.columns))):
                    val = sheet_df.iloc[i, j]
                    if pd.notna(val):
                        search_text += str(val) + " "
        except Exception:
            pass

    search_lower = search_text.lower()

    # Check for INR indicators
    if any(kw in search_lower for kw in ["inr", "₹", "crore", "cr", "lakh", "lakhs", "rupee"]):
        return "INR"

    # Check for USD indicators
    if any(kw in search_lower for kw in ["usd", "$", "dollar"]):
        return "USD"

    # Check metric names for $ sign (like "Bookings (new customers) $")
    if "$" in search_text:
        return "USD"

    return "USD"  # Default


def parse_mis_excel(
    file_path: str,
    company_id,
    db,
    sheet_name: str = None
):
    """
    Parse ALL relevant sheets in a Salesforce MIS Excel export.
    Merges metrics from multiple sheets into unified per-period records.
    """
    from app.models.company import Company
    from app.models.portfolio_metrics import PortfolioMetrics

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise ValueError(f"Company not found: {company_id}")

    company_type = detect_company_type(company.market_tags or [])
    logger.info(f"Parsing MIS for {company.name} (type: {company_type}) from {file_path}")

    xls = pd.ExcelFile(file_path)
    upload_batch = f"{datetime.now().strftime('%Y%m%d')}_{company.name.lower().replace(' ', '_')}"

    # Determine sheets to parse — include business + financial, skip cash flow for now
    sheets_to_parse = []
    for sn in xls.sheet_names:
        sn_lower = sn.lower()
        if any(kw in sn_lower for kw in ["business", "financial", "metric", "p&l", "pnl", "revenue", "income"]):
            sheets_to_parse.append(sn)

    if not sheets_to_parse:
        sheets_to_parse = xls.sheet_names[:2]

    if sheet_name and sheet_name in xls.sheet_names:
        sheets_to_parse = [sheet_name]

    logger.info(f"Parsing sheets: {sheets_to_parse}")

    # Detect currency
    currency = detect_currency(pd.DataFrame(), sheets_to_parse, file_path)
    logger.info(f"Detected currency: {currency}")

    all_metrics_by_period = {}
    all_metric_names = []
    total_columns_meta = []

    for sn in sheets_to_parse:
        logger.info(f"  Processing sheet: {sn}")
        df = pd.read_excel(file_path, sheet_name=sn, header=None)

        # Detect structure
        date_row_idx = None
        label_row_idx = None
        data_start_col = None

        for row_idx in range(min(5, len(df))):
            for col_idx in range(min(20, len(df.columns))):
                val = df.iloc[row_idx, col_idx]
                if isinstance(val, (datetime, pd.Timestamp)):
                    date_row_idx = row_idx
                    if date_row_idx > 0:
                        label_row_idx = date_row_idx - 1
                    data_start_col = col_idx
                    break
            if date_row_idx is not None:
                break

        if date_row_idx is None:
            logger.warning(f"  No date row found in {sn}, skipping")
            continue

        # Find metric name column
        metric_name_col = None
        for col_idx in range(data_start_col - 1, -1, -1):
            text_count = sum(1 for r in range(date_row_idx + 1, min(date_row_idx + 15, len(df)))
                          if pd.notna(df.iloc[r, col_idx]) and isinstance(df.iloc[r, col_idx], str))
            if text_count >= 3:
                metric_name_col = col_idx
                break
        if metric_name_col is None:
            metric_name_col = data_start_col - 1

        sheet_metrics, sheet_names, sheet_cols = _parse_single_sheet(
            df, company_id, company_type,
            date_row_idx, label_row_idx, metric_name_col, data_start_col,
            db, upload_batch, file_path.split("/")[-1], sn
        )

        # Merge
        for key, metrics_dict in sheet_metrics.items():
            if key not in all_metrics_by_period:
                all_metrics_by_period[key] = {}
            all_metrics_by_period[key].update(metrics_dict)

        for name in sheet_names:
            if name not in all_metric_names:
                all_metric_names.append(name)

        if not total_columns_meta:
            total_columns_meta = sheet_cols

        logger.info(f"  Found {len(sheet_names)} metrics in {sn}")

    # Store (upsert)
    periods_stored = 0
    periods_updated = 0

    for (period_date, is_projected), metrics_dict in all_metrics_by_period.items():
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
            existing.currency = currency
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
                currency=currency,
                upload_batch=upload_batch,
            )
            db.add(pm)
            periods_stored += 1

    # AI-powered headline selection
    logger.info("🤖 Selecting headline metrics with AI...")
    select_headline_metrics_with_ai(
        company_name=company.name,
        company_type=company_type,
        metric_names=all_metric_names,
        db=db,
        company_id=company_id,
        currency=currency,
    )

    db.commit()

    category_counts = {}
    for name in all_metric_names:
        cat, _ = classify_metric(name, company_type)
        category_counts.setdefault(cat, 0)
        category_counts[cat] += 1

    return {
        "company": company.name,
        "company_type": company_type,
        "sheets_parsed": sheets_to_parse,
        "metrics_found": len(all_metric_names),
        "periods_new": periods_stored,
        "periods_updated": periods_updated,
        "date_range": f"{total_columns_meta[0]['label']} to {total_columns_meta[-1]['label']}" if total_columns_meta else "none",
        "metric_categories": category_counts,
        "upload_batch": upload_batch,
        "currency": currency,
    }
