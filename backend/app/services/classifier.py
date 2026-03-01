import logging
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

# Categories for classification
CATEGORIES = [
    "product",  # Features, launches, integrations, technical updates
    "gtm",  # Pricing, packaging, sales, partnerships, market expansion
    "traction",  # Customer metrics, ARR, user growth, retention
    "market_position",  # Awards, analyst reports, competitive wins
    "corporate",  # Funding, M&A, leadership, strategic pivots
    "regulatory",  # Compliance, certifications, security incidents
]

# Cheap models for classification (simple task)
PRIMARY_MODEL = "google/gemini-flash-1.5"
FALLBACK_MODEL = "meta-llama/llama-3.1-8b-instruct:free"
EXPENSIVE_MODEL = "anthropic/claude-sonnet-4-20250514"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)


def classify_content(content: str, company_name: str = "") -> str:
    """
    Classify content into one of 6 categories using cheap models.
    Returns category name or 'corporate' as default.
    """
    if not content or len(content.strip()) < 20:
        return "corporate"

    prompt = f"""Classify the following content into ONE of these categories:
- product: Features, launches, integrations, technical updates
- gtm: Pricing, packaging, sales, partnerships, market expansion
- traction: Customer metrics, ARR, user growth, retention
- market_position: Awards, analyst reports, competitive wins
- corporate: Funding, M&A, leadership, strategic pivots
- regulatory: Compliance, certifications, security incidents

Content about {company_name}:
{content[:2000]}

Respond with ONLY the category name (one word)."""

    models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL, EXPENSIVE_MODEL]

    for model in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a content classifier. Respond with only the category name."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0.1,
            )

            result = response.choices[0].message.content.strip().lower()

            # Validate result is a valid category
            if result in CATEGORIES:
                logger.info(f"Classification successful with {model}: {result}")
                return result

            # If result contains a category, extract it
            for cat in CATEGORIES:
                if cat in result:
                    logger.info(f"Classification successful with {model} (extracted): {cat}")
                    return cat

            logger.warning(f"Invalid classification result from {model}: {result}")

        except Exception as e:
            logger.error(f"Error classifying with {model}: {e}")
            continue

    # Default fallback
    logger.warning("All classification models failed, defaulting to 'corporate'")
    return "corporate"

