"""
AI-powered relevance filtering for intelligence items.
Uses Claude Haiku to determine if content is relevant to board members.
"""
import logging
import json
import re
from typing import Dict, Any
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

# Use Claude Haiku for relevance checking
MODEL = "anthropic/claude-3.5-haiku"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)


def check_relevance(
    content: str,
    title: str,
    company_name: str,
    market_tags: list[str]
) -> Dict[str, Any]:
    """
    Check if content is relevant to board members using Claude Haiku.
    
    Raises exception if API call fails - no fallback values.
    
    Returns:
        {
            "is_relevant": bool,
            "relevance_score": float (0.0-1.0),
            "reason": str,
            "category": str,
            "summary": str
        }
    """
    if not content or len(content.strip()) < 50:
        return {
            "is_relevant": False,
            "relevance_score": 0.0,
            "reason": "Content too short",
            "category": "corporate",
            "summary": ""
        }
    
    # Build market description from tags
    market_description = ", ".join(market_tags[:5]) if market_tags else "technology"
    
    # Truncate content for prompt (keep first 3000 chars)
    content_preview = content[:3000]
    title_preview = title[:200]
    
    prompt = f"""You are a senior investment analyst evaluating market intelligence for {company_name}, a {market_description} company, on behalf of General Partners at a top-tier VC firm.

ONLY flag items as relevant if a GP would mention them in a Monday partners meeting. Be VERY selective — reject 70%+ of content.

✅ RELEVANT (score 0.7-1.0):
- {company_name} directly mentioned: funding, revenue milestones, product launches, leadership changes, major customer wins/losses
- Named competitors (like {', '.join(market_tags[:3]) if market_tags else 'key players'}) raising capital, launching products, making acquisitions, or losing key deals
- Analyst/expert commentary from Gartner, Forrester, IDC, G2 specifically about {company_name} or its direct competitors
- Market size updates, regulatory changes, or shifts that directly impact {company_name}'s TAM or competitive position
- Strategic partnerships, channel deals, or geographic expansion by {company_name} or direct competitors

❌ NOT RELEVANT (score 0.0-0.3) — REJECT these:
- Generic industry news that doesn't name {company_name} or a direct competitor
- Companies getting SOC 2 / ISO certified (unless it's {company_name} or a competitor)
- Blog posts, thought leadership, or marketing content
- Minor product updates, webinars, or events
- Tangentially related companies in adjacent markets
- Reddit posts that are generic discussions without specific company insights
- News about companies that happen to be in the same broad industry but aren't competitors

CRITICAL: If the content doesn't name {company_name} or one of its specific competitors, it is almost certainly NOT relevant. Generic market commentary is NOT relevant.

Content to evaluate:
Title: {title_preview}
Content: {content_preview}

Return JSON only (no markdown):
{{
  "is_relevant": true/false,
  "relevance_score": 0.0-1.0,
  "reason": "One sentence: why a GP would or wouldn't care",
  "category": "product/gtm/traction/market_position/corporate/regulatory/funding",
  "summary": "2-3 sentences: What happened, who is involved, and what it means for {company_name}. Be specific with names, numbers, and strategic implications."
}}"""

    # Make API call - raise exception if it fails
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are an intelligence analyst. Return only valid JSON, no markdown formatting."
            },
            {"role": "user", "content": prompt}
        ],
        max_tokens=300,
        temperature=0.2,
    )
    
    result_text = response.choices[0].message.content.strip()
    
    # Clean up JSON (remove markdown code blocks if present)
    result_text = re.sub(r'```json\s*', '', result_text)
    result_text = re.sub(r'```\s*', '', result_text)
    result_text = result_text.strip()
    
    # Parse JSON - raise exception if parsing fails
    result = json.loads(result_text)
    
    # Validate structure
    if not isinstance(result, dict):
        raise ValueError("Response is not a dictionary")
    
    # Ensure all required fields
    result.setdefault("is_relevant", False)
    result.setdefault("relevance_score", 0.0)
    result.setdefault("reason", "No reason provided")
    result.setdefault("category", "corporate")
    result.setdefault("summary", "")
    
    # Validate category
    valid_categories = ["product", "gtm", "traction", "market_position", "corporate", "regulatory", "funding"]
    if result["category"] not in valid_categories:
        result["category"] = "corporate"
    
    # Clamp relevance score
    result["relevance_score"] = max(0.0, min(1.0, float(result["relevance_score"])))
    
    logger.debug(f"✅ Relevance check successful: {result['is_relevant']} (score: {result['relevance_score']})")
    return result
