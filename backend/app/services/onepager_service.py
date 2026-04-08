import json
from datetime import datetime, timedelta
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.company import Company
from app.models.onepager import CompanyOnePager, StanceEnum
from app.models.portfolio_metrics import MetricsCatalog, PortfolioMetrics

async def generate_onepager(company_id: UUID, db: Session) -> dict:
    """Generate a one-pager by aggregating all data sources and calling Claude Haiku."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise ValueError(f"Company {company_id} not found")

    metrics_data = _gather_metrics(company_id, db)
    doc_content, documents_used = _gather_documents(company_id, db)
    intel_items = _gather_intelligence(company_id, db)
    company_type = _detect_company_type(company.market_tags or [])

    prompt = _build_onepager_prompt(
        company_name=company.name,
        company_type=company_type,
        market_tags=company.market_tags or [],
        competitors=company.competitors or [],
        metrics_data=metrics_data,
        doc_content=doc_content,
        intel_items=intel_items,
    )

    result = await _call_llm(prompt)
    return _parse_and_save(company_id, result, metrics_data, documents_used, intel_items, db)


def _gather_metrics(company_id: UUID, db: Session) -> dict:
    """Get latest metrics + catalog for the company."""
    metrics = (
        db.query(PortfolioMetrics)
        .filter(
            PortfolioMetrics.company_id == company_id,
            PortfolioMetrics.is_projected == False,
        )
        .order_by(PortfolioMetrics.period.desc())
        .limit(6)
        .all()
    )

    catalog = db.query(MetricsCatalog).filter(MetricsCatalog.company_id == company_id).all()
    headline_metrics = [c for c in catalog if c.is_headline]

    return {
        "periods": [
            {
                "period": m.period.isoformat(),
                "period_label": m.period_label,
                "metrics": m.metrics,
                "currency": m.currency or "USD",
            }
            for m in metrics
        ],
        "catalog": {
            c.raw_name: {
                "display_name": c.display_name,
                "category": c.category,
                "unit": c.unit,
                "is_headline": c.is_headline,
            }
            for c in catalog
        },
        "headline_names": [c.display_name for c in headline_metrics],
    }


def _gather_documents(company_id: UUID, db: Session) -> tuple[str, list[dict]]:
    """Get recent document summaries and chunk content."""
    from app.models.document import DocumentChunk, PortfolioDocument

    docs = (
        db.query(PortfolioDocument)
        .filter(
            PortfolioDocument.company_id == company_id,
            PortfolioDocument.is_active == True,
        )
        .order_by(PortfolioDocument.document_date.desc())
        .limit(3)
        .all()
    )

    content_parts = []
    documents_used = []
    for doc in docs:
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == doc.id)
            .order_by(DocumentChunk.chunk_index)
            .limit(10)
            .all()
        )

        doc_text = f"\n--- Document: {doc.title} ({doc.document_date}) ---\n"
        if doc.summary:
            doc_text += f"Summary: {doc.summary}\n"
        for chunk in chunks:
            doc_text += chunk.chunk_text + "\n"
        content_parts.append(doc_text)
        documents_used.append(
            {
                "id": str(doc.id),
                "title": doc.title,
                "date": doc.document_date.isoformat() if doc.document_date else None,
            }
        )

    return "\n".join(content_parts), documents_used


def _gather_intelligence(company_id: UUID, db: Session) -> list:
    """Get recent intelligence items."""
    from app.models.intelligence import IntelligenceItem

    cutoff = datetime.utcnow() - timedelta(days=30)
    items = (
        db.query(IntelligenceItem)
        .filter(
            IntelligenceItem.company_id == company_id,
            IntelligenceItem.published_date >= cutoff,
            IntelligenceItem.relevance_score >= 60,
        )
        .order_by(IntelligenceItem.published_date.desc())
        .limit(15)
        .all()
    )

    return [
        {
            "title": item.title,
            "summary": item.summary or item.title,
            "source": item.source_type,
            "category": item.result_category or "general",
            "date": item.published_date.isoformat() if item.published_date else None,
        }
        for item in items
    ]


def _detect_company_type(market_tags: list) -> str:
    tags_lower = [t.lower() for t in market_tags]
    tag_str = " ".join(tags_lower)

    if any(kw in tag_str for kw in ["saas", "compliance", "grc", "observability", "management platform"]):
        return "saas"
    if any(kw in tag_str for kw in ["fintech", "investment", "deposits", "wealth", "lending", "payments"]):
        return "fintech"
    if any(kw in tag_str for kw in ["consumer", "commerce", "home services", "hyperlocal", "gig economy"]):
        return "consumer"
    if any(kw in tag_str for kw in ["deeptech", "satellite", "ai research", "robotics"]):
        return "deeptech"
    return "saas"


def _build_onepager_prompt(
    company_name: str,
    company_type: str,
    market_tags: list,
    competitors: list,
    metrics_data: dict,
    doc_content: str,
    intel_items: list,
) -> str:
    metrics_focus = {
        "saas": "ARR/MRR, Revenue Growth %, Net Revenue Retention, Burn Multiple, Cash Runway (months), Gross Margin, Customer Count, Logo Churn",
        "fintech": "AUM, Revenue, Active Users, CAC, LTV, Take Rate, Regulatory Milestones, Cash Position",
        "consumer": "GMV, Order Volume, AOV, Repeat Rate, CAC, Contribution Margin, MAU/DAU, Cash Burn",
        "deeptech": "Revenue (if any), Contract Pipeline, Tech Milestones, Cash Runway, IP Portfolio, Key Partnerships",
    }

    intel_text = "\n".join(
        [
            f"- [{item['category']}] {item['title']}: {item['summary']} (Source: {item['source']}, {item['date']})"
            for item in intel_items
        ]
    ) if intel_items else "No recent intelligence items available."

    metrics_text = json.dumps(metrics_data, indent=2, default=str)

    return f"""You are a portfolio analyst at Lightspeed India Partners, writing a weekly portfolio update one-pager for {company_name}.

COMPANY CONTEXT:
- Name: {company_name}
- Type: {company_type}
- Market: {', '.join(market_tags[:5])}
- Key competitors: {', '.join(competitors[:5])}

AVAILABLE DATA:

1. FINANCIAL METRICS (from MIS data):
{metrics_text}

2. INTERNAL DOCUMENTS (board decks, updates):
{doc_content[:6000]}

3. RECENT MARKET INTELLIGENCE (last 30 days):
{intel_text}

TASK: Generate a structured one-pager in the Lightspeed weekly portfolio format. Return ONLY valid JSON with this exact structure:

{{
  "stance": "green" | "yellow" | "red",
  "stance_summary": "1-2 sentence overall assessment",
  "next_milestone": "Key upcoming milestone with rough timeline",
  "metrics_table": [
    {{
      "metric_name": "Display Name",
      "current_value": "formatted value e.g. $2.3M or 45%",
      "previous_value": "formatted previous period value",
      "change_pct": "+12%" or "-5%",
      "trend": "up" | "down" | "flat",
      "unit": "currency" | "percentage" | "number" | "months"
    }}
  ],
  "performance_narrative": [
    "Bullet 1 explaining key metric trends",
    "Bullet 2 on revenue/growth drivers",
    "Bullet 3 on efficiency or unit economics"
  ],
  "working_well": [
    "Strategic highlight 1 — concrete, specific, backed by data",
    "Strategic highlight 2",
    "Strategic highlight 3"
  ],
  "needs_improvement": [
    "Concern 1 — specific with data point if available",
    "Concern 2",
    "Concern 3"
  ],
  "value_creation": [
    "Action item 1 for the Lightspeed team — specific and actionable",
    "Action item 2",
    "Action item 3"
  ]
}}

GUIDELINES:
- For metrics_table, focus on these key metrics for {company_type} companies: {metrics_focus.get(company_type, metrics_focus['saas'])}
- Only include metrics that have actual data. Format numbers cleanly (₹2.3Cr, $1.5M, 45%, 3.2x).
- For currency: detect from the data whether values are in INR (Cr/Lakhs) or USD (M/K). Preserve the original currency.
- stance should reflect the overall trajectory: green = above plan + strong execution, yellow = mixed signals or behind on some metrics, red = significant misses or structural concerns.
- working_well should blend internal performance (from metrics/docs) with external validation (from intelligence items like awards, market recognition).
- needs_improvement should be honest but constructive — these are for internal LP discussion.
- value_creation should be specific to what a VC firm can do: help with hiring, customer intros, strategic advice, board-level guidance, fundraise support.
- Keep each bullet to 1-2 sentences max. Be specific, not generic.
- If data is limited, say so honestly rather than fabricating. Mark sections with "[Limited data]" prefix if needed.

Return ONLY the JSON object, no markdown fences, no preamble."""


async def _call_llm(prompt: str) -> dict:
    """Call Claude Haiku via OpenRouter."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "anthropic/claude-3.5-haiku",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.3,
            },
        )
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    return json.loads(content)


def _parse_and_save(
    company_id: UUID,
    result: dict,
    metrics_data: dict,
    documents_used: list[dict],
    intel_items: list,
    db: Session,
) -> dict:
    """Parse LLM result and save to database."""
    db.query(CompanyOnePager).filter(
        CompanyOnePager.company_id == company_id,
        CompanyOnePager.is_latest == True,
    ).update({"is_latest": False})

    now = datetime.utcnow()
    period_label = now.strftime("%b %Y")
    stance_raw = str(result.get("stance", "yellow")).lower()
    if stance_raw not in {"green", "yellow", "red"}:
        stance_raw = "yellow"

    onepager = CompanyOnePager(
        company_id=company_id,
        generated_at=now,
        generated_by="ai",
        is_latest=True,
        period_label=period_label,
        stance=StanceEnum(stance_raw),
        stance_summary=result.get("stance_summary", ""),
        next_milestone=result.get("next_milestone", ""),
        metrics_table=result.get("metrics_table", []),
        performance_narrative=result.get("performance_narrative", []),
        working_well=result.get("working_well", []),
        needs_improvement=result.get("needs_improvement", []),
        value_creation=result.get("value_creation", []),
        data_sources={
            "metrics_periods": [p["period_label"] for p in metrics_data.get("periods", [])],
            "documents_used": documents_used,
            "intelligence_count": len(intel_items),
        },
    )
    db.add(onepager)
    db.commit()
    db.refresh(onepager)
    return _serialize_onepager(onepager)


def _serialize_onepager(op: CompanyOnePager) -> dict:
    return {
        "id": str(op.id),
        "company_id": str(op.company_id),
        "generated_at": op.generated_at.isoformat() if op.generated_at else None,
        "generated_by": op.generated_by,
        "is_latest": op.is_latest,
        "period_label": op.period_label,
        "stance": op.stance.value if op.stance else "yellow",
        "stance_summary": op.stance_summary,
        "next_milestone": op.next_milestone,
        "metrics_table": op.metrics_table or [],
        "performance_narrative": op.performance_narrative or [],
        "working_well": op.working_well or [],
        "needs_improvement": op.needs_improvement or [],
        "value_creation": op.value_creation or [],
        "data_sources": op.data_sources or {},
        "last_edited_at": op.last_edited_at.isoformat() if op.last_edited_at else None,
        "edit_history": op.edit_history or [],
    }


def get_latest_onepager(company_id: UUID, db: Session) -> dict | None:
    op = db.query(CompanyOnePager).filter(
        CompanyOnePager.company_id == company_id,
        CompanyOnePager.is_latest == True,
    ).first()
    if not op:
        return None
    return _serialize_onepager(op)


def update_onepager_field(onepager_id: UUID, field: str, value, db: Session) -> dict:
    EDITABLE_FIELDS = {
        "stance",
        "stance_summary",
        "next_milestone",
        "metrics_table",
        "performance_narrative",
        "working_well",
        "needs_improvement",
        "value_creation",
    }
    if field not in EDITABLE_FIELDS:
        raise ValueError(f"Field '{field}' is not editable")

    op = db.query(CompanyOnePager).filter(CompanyOnePager.id == onepager_id).first()
    if not op:
        raise ValueError("One-pager not found")

    old_value = getattr(op, field)
    if field == "stance":
        value = StanceEnum(str(value).lower())

    setattr(op, field, value)
    op.last_edited_at = datetime.utcnow()
    op.generated_by = "manual"

    history = op.edit_history or []
    history.append(
        {
            "field": field,
            "old_value": old_value,
            "new_value": value,
            "edited_at": datetime.utcnow().isoformat(),
        }
    )
    op.edit_history = history

    db.commit()
    db.refresh(op)
    return _serialize_onepager(op)
