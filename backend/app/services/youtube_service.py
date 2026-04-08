import json
import subprocess
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session
from youtube_transcript_api import YouTubeTranscriptApi

from app.core.config import settings
from app.models.company import Company
from app.models.intelligence import IntelligenceItem
from app.models.youtube_scan import YouTubeScan
from app.services.dedup_helper import is_duplicate_title


def _generate_search_queries(company: Company) -> list:
    """Generate YouTube search queries across multiple dimensions per competitor."""
    queries = []
    competitors = company.competitors or []
    market_tags = company.market_tags or []

    search_dimensions = [
        "{competitor} CEO interview",
        "{competitor} CRO interview",
        "{competitor} product launch",
        "{competitor} GTM strategy",
        "{competitor} AI features",
        "{competitor} growth metrics",
        "{competitor} business model",
        "{competitor} funding valuation",
        "{competitor} earnings results",
    ]

    for competitor in competitors[:4]:
        for template in search_dimensions:
            queries.append(template.format(competitor=competitor))

    for competitor in competitors[4:7]:
        queries.append(f"{competitor} CEO interview")
        queries.append(f"{competitor} product strategy")

    if market_tags:
        tag_str = " ".join(market_tags[:3])
        queries.append(f"{tag_str} market trends")
        queries.append(f"{tag_str} industry analysis")
        queries.append(f"{tag_str} India market")

    queries.append(f"{company.name} interview")
    queries.append(f"{company.name} startup")

    comp_tickers = getattr(company, "comp_tickers", None) or {}
    for comp_name, ticker in comp_tickers.items():
        if ticker:
            queries.append(f"{comp_name} earnings call Q1 2026")
            queries.append(f"{comp_name} investor presentation")

    return queries


def _search_youtube(query: str, max_results: int = 5, days_back: int = 14) -> list:
    """Search YouTube using yt-dlp and return video metadata. No API key needed."""
    try:
        cmd = [
            "yt-dlp",
            f"ytsearch{max_results}:{query}",
            "--dump-json",
            "--flat-playlist",
            "--no-download",
            "--quiet",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return []

        videos = []
        cutoff = datetime.utcnow() - timedelta(days=days_back)
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                video_id = data.get("id", "")
                title = data.get("title", "")
                channel = data.get("channel", "") or data.get("uploader", "")

                upload_date_str = data.get("upload_date", "")
                published = None
                if upload_date_str and len(upload_date_str) == 8:
                    try:
                        published = datetime.strptime(upload_date_str, "%Y%m%d")
                    except ValueError:
                        pass

                if published and published < cutoff:
                    continue

                duration = data.get("duration", 0) or 0
                if duration > 0 and duration < 120:
                    continue

                videos.append(
                    {
                        "video_id": video_id,
                        "title": title,
                        "channel_name": channel,
                        "published": published,
                        "duration": duration,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                    }
                )
            except json.JSONDecodeError:
                continue
        return videos
    except subprocess.TimeoutExpired:
        return []
    except Exception:
        return []


def _get_transcript(video_id: str) -> Optional[str]:
    """Get transcript for a YouTube video. Returns None if unavailable."""
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)
        full_text = " ".join([snippet.text for snippet in transcript])
        return full_text.strip()
    except Exception:
        return None


async def _analyze_transcript(
    video_title: str,
    transcript: str,
    channel_name: str,
    search_query: str,
    company: Company,
) -> dict:
    """Use Claude Haiku to analyze transcript for portfolio-relevant insights."""
    company_context = f"""Company: {company.name}
Market: {', '.join((company.market_tags or [])[:5])}
Competitors: {', '.join((company.competitors or [])[:7])}"""

    words = transcript.split()
    if len(words) > 4000:
        transcript_trimmed = " ".join(words[:2000]) + "\n\n[...middle omitted...]\n\n" + " ".join(words[-2000:])
    else:
        transcript_trimmed = transcript

    prompt = f"""You are an analyst at Lightspeed India Partners reviewing a YouTube video transcript for insights relevant to a specific portfolio company.

VIDEO: "{video_title}"
CHANNEL: {channel_name}
SEARCH CONTEXT: Found via search "{search_query}"

PORTFOLIO COMPANY:
{company_context}

TRANSCRIPT:
{transcript_trimmed}

TASK: Extract insights that would be valuable for {company.name}'s founders, board members, or the Lightspeed investment team. Be VERY STRICT — only flag insights that are genuinely actionable or strategically important for THIS specific company.

Return ONLY valid JSON:
{{
  "relevance_score": 0-100,
  "insights": [
    {{
      "title": "Concise insight headline (max 15 words)",
      "summary": "2-3 sentence summary with specific details from the transcript",
      "category": "competitive_intel" | "market_trend" | "strategy" | "technology" | "fundraising" | "hiring"
    }}
  ]
}}

STRICT RULES:
- 0-30: Not relevant to {company.name}. Generic advice or unrelated content.
- 30-59: Tangentially relevant but no actionable insight.
- 60-79: Relevant — useful market intelligence, competitor moves, or strategic context.
- 80-100: Highly relevant — direct competitor strategy shift, critical market change.

Only include insights that a board member would actually want to know. Skip generic startup advice. If nothing is relevant, return score 0 and empty insights array.

Return ONLY JSON, no markdown fences."""

    try:
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
                    "max_tokens": 1000,
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content.strip())
    except Exception:
        return {"relevance_score": 0, "insights": []}


def _create_intelligence_items(
    company_id: UUID,
    scan: YouTubeScan,
    analysis: dict,
    db: Session,
) -> int:
    """Create one combined intelligence_item per analyzed video."""
    insights = analysis.get("insights", []) or []
    if not insights:
        return 0

    # One item per video URL; skip if already present.
    existing = db.query(IntelligenceItem).filter(
        IntelligenceItem.source_url == scan.video_url
    ).first()
    if existing:
        return 0

    title = insights[0].get("title", "YouTube insight")
    if is_duplicate_title(db, company_id, title):
        return 0

    summaries = [i.get("summary", "").strip() for i in insights if i.get("summary")]
    combined_summary = "\n\n".join(summaries).strip()
    if not combined_summary:
        combined_summary = scan.video_title or "YouTube insight"

    categories = [i.get("category") for i in insights if i.get("category")]
    category = Counter(categories).most_common(1)[0][0] if categories else "competitive_intel"

    item = IntelligenceItem(
        company_id=company_id,
        title=title,
        summary=combined_summary,
        full_content=scan.transcript_text[:20000] if scan.transcript_text else None,
        source_type="youtube",
        source_url=scan.video_url,
        result_category=category,
        relevance_score=float(analysis.get("relevance_score", 60)),
        published_date=scan.published_at,
        extra_data={
            "source_name": f"YouTube: {scan.channel_name or 'Unknown'}",
            "video_id": scan.video_id,
            "search_query": scan.search_query,
            "insight_count": len(insights),
        },
    )

    # Gracefully handle URL uniqueness races without failing the scan.
    try:
        with db.begin_nested():
            db.add(item)
            db.flush()
        return 1
    except Exception:
        return 0


async def scan_company_youtube(company_id: UUID, db: Session, days_back: int = 14, max_queries: int = 20) -> dict:
    """Search YouTube for videos relevant to a specific portfolio company."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise ValueError("Company not found")

    all_queries = _generate_search_queries(company)
    queries = all_queries[:max_queries]
    stats = {
        "company": company.name,
        "queries_run": len(queries),
        "videos_found": 0,
        "transcripts_fetched": 0,
        "insights_created": 0,
        "queries_detail": [],
    }
    seen_video_ids = set()

    for query in queries:
        query_stats = {"query": query, "videos": 0, "relevant": 0}
        videos = _search_youtube(query, max_results=3, days_back=days_back)

        for video in videos:
            video_id = video["video_id"]
            if video_id in seen_video_ids:
                continue
            seen_video_ids.add(video_id)

            stats["videos_found"] += 1
            query_stats["videos"] += 1

            existing = db.query(YouTubeScan).filter(
                YouTubeScan.video_id == video_id,
                YouTubeScan.company_id == company_id,
            ).first()
            if existing:
                continue

            transcript = _get_transcript(video_id)
            if not transcript:
                scan = YouTubeScan(
                    company_id=company_id,
                    video_id=video_id,
                    video_title=video["title"],
                    video_url=video["url"],
                    channel_name=video.get("channel_name"),
                    published_at=video.get("published"),
                    search_query=query,
                    transcript_length=0,
                    processed=True,
                    relevance_score=0,
                    processed_at=datetime.utcnow(),
                )
                db.add(scan)
                db.commit()
                continue

            stats["transcripts_fetched"] += 1
            analysis = await _analyze_transcript(
                video_title=video["title"],
                transcript=transcript,
                channel_name=video.get("channel_name", ""),
                search_query=query,
                company=company,
            )

            scan = YouTubeScan(
                company_id=company_id,
                video_id=video_id,
                video_title=video["title"],
                video_url=video["url"],
                channel_name=video.get("channel_name"),
                published_at=video.get("published"),
                search_query=query,
                transcript_text=transcript[:50000],
                transcript_length=len(transcript),
                processed=True,
                relevance_score=int(analysis.get("relevance_score", 0)),
                insights=analysis.get("insights", []),
                processed_at=datetime.utcnow(),
            )
            db.add(scan)

            if analysis.get("relevance_score", 0) >= 60:
                insights_count = _create_intelligence_items(
                    company_id=company_id, scan=scan, analysis=analysis, db=db
                )
                stats["insights_created"] += insights_count
                query_stats["relevant"] += insights_count

            db.commit()

        stats["queries_detail"].append(query_stats)

    return stats


async def scan_all_companies_youtube(db: Session, days_back: int = 14) -> dict:
    """Scan YouTube for all active portfolio companies."""
    companies = db.query(Company).filter(
        Company.name.in_(["Scrut Automation", "Snabbit", "Stable Money"])
    ).all()

    all_stats = {"companies_scanned": 0, "total_insights": 0, "results": []}
    for company in companies:
        try:
            company_stats = await scan_company_youtube(company.id, db, days_back=days_back)
            all_stats["companies_scanned"] += 1
            all_stats["total_insights"] += company_stats["insights_created"]
            all_stats["results"].append(company_stats)
        except Exception as e:
            all_stats["results"].append({"company": company.name, "error": str(e)})

    return all_stats


def get_company_scans(company_id: UUID, db: Session, limit: int = 20) -> list:
    """Get recent YouTube scans for a company."""
    scans = db.query(YouTubeScan).filter(
        YouTubeScan.company_id == company_id,
        YouTubeScan.processed == True,
    ).order_by(YouTubeScan.created_at.desc()).limit(limit).all()

    return [
        {
            "id": str(s.id),
            "video_id": s.video_id,
            "video_title": s.video_title,
            "video_url": s.video_url,
            "channel_name": s.channel_name,
            "published_at": s.published_at.isoformat() if s.published_at else None,
            "search_query": s.search_query,
            "transcript_length": s.transcript_length,
            "relevance_score": s.relevance_score,
            "insights": s.insights,
        }
        for s in scans
    ]
