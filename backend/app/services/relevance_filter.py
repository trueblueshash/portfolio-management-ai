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
    
    prompt = f"""You are evaluating intelligence for {company_name}, a {market_description} company.

Board members care about:
✅ Strategic moves: Funding, M&A, major partnerships, market expansion
✅ Competitive threats: Competitor product launches, big customer wins, pricing changes
✅ Market validation: Awards, analyst recognition, customer traction metrics
✅ Risks: Major customer losses, security incidents, regulatory issues
✅ Product signals: Major feature launches, technology breakthroughs
✅ Customer signals: Significant complaints/praise patterns, churn indicators

Board members DON'T care about:
❌ Routine blog posts
❌ Generic marketing content
❌ Minor feature updates
❌ Unrelated industry news
❌ Individual customer support issues

Content to evaluate:
Title: {title_preview}
Content: {content_preview}

Return JSON (no markdown, just raw JSON):
{{
  "is_relevant": true/false,
  "relevance_score": 0.0-1.0,
  "reason": "Why this matters to board members (or why not)",
  "category": "product/gtm/traction/market_position/corporate/regulatory",
  "summary": "2-3 sentence summary of what happened and impact"
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
    valid_categories = ["product", "gtm", "traction", "market_position", "corporate", "regulatory"]
    if result["category"] not in valid_categories:
        result["category"] = "corporate"
    
    # Clamp relevance score
    result["relevance_score"] = max(0.0, min(1.0, float(result["relevance_score"])))
    
    logger.debug(f"✅ Relevance check successful: {result['is_relevant']} (score: {result['relevance_score']})")
    return result
