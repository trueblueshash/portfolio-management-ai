import logging
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

# Cheap models for summarization
PRIMARY_MODEL = "anthropic/claude-3.5-haiku"  # Cheap, high quality
FALLBACK_MODEL = "google/gemini-flash-1.5"  # Free
EXPENSIVE_MODEL = "anthropic/claude-sonnet-4-20250514"  # Only when needed

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)


def needs_expensive_model(content: str) -> bool:
    """Determine if content is complex enough to warrant expensive model"""
    # Use expensive model if:
    # - Content is very long (>5000 chars)
    # - Contains technical keywords
    if len(content) > 5000:
        return True

    technical_keywords = [
        "algorithm", "architecture", "infrastructure", "protocol", "API", "SDK",
        "framework", "implementation", "optimization", "scalability", "performance"
    ]
    content_lower = content.lower()
    if any(keyword in content_lower for keyword in technical_keywords):
        return True

    return False


def summarize_content(content: str, company_name: str = "", market_context: str = "") -> str:
    """
    Generate 2-3 sentence summary using cost-optimized models.
    Returns summary or truncated content if all models fail.
    """
    if not content:
        return "No content available."

    # Truncate content for prompt (keep first 4000 chars)
    content_preview = content[:4000]

    # Determine which model to use
    use_expensive = needs_expensive_model(content)
    models_to_try = [EXPENSIVE_MODEL] if use_expensive else [PRIMARY_MODEL, FALLBACK_MODEL, EXPENSIVE_MODEL]

    prompt = f"""Create a concise 2-3 sentence summary of the following content.

Company: {company_name}
Context: {market_context}

Focus on: what happened, why it matters, and any key metrics or numbers.

Content:
{content_preview}

Summary:"""

    for model in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a content summarizer. Create concise, informative summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3,
            )

            summary = response.choices[0].message.content.strip()

            # Quality check: summary should be reasonable length
            if len(summary) >= 50:
                logger.info(f"Summarization successful with {model}")
                return summary
            else:
                logger.warning(f"Summary too short from {model}: {summary}")

        except Exception as e:
            logger.error(f"Error summarizing with {model}: {e}")
            continue

    # Final fallback: return truncated content
    logger.warning("All summarization models failed, using truncated content")
    if len(content) > 200:
        return content[:200] + "..."
    return content

