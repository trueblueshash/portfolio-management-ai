import logging
import feedparser
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.company import Company
from app.models.intelligence import IntelligenceItem
from app.services.dedup_helper import is_duplicate_title
from app.services.summarizer import summarize_content
from app.services.classifier import classify_content

logger = logging.getLogger(__name__)


def calculate_relevance_score(content: str, market_tags: list[str], competitors: list[str]) -> float:
    """Calculate relevance score based on keyword matches"""
    if not content:
        return 0.0

    content_lower = content.lower()
    matches = 0
    total_keywords = len(market_tags) + len(competitors)

    if total_keywords == 0:
        return 0.5  # Default relevance if no keywords

    # Check market tags
    for tag in market_tags:
        if tag.lower() in content_lower:
            matches += 1

    # Check competitors
    for competitor in competitors:
        if competitor.lower() in content_lower:
            matches += 1

    score = matches / total_keywords
    return min(score, 1.0)  # Cap at 1.0


def scrape_company_blog(company: Company, db: Session) -> int:
    """
    Scrape RSS blog feed for a company.
    Returns number of new items added.
    """
    if not company.sources or "blog" not in company.sources:
        logger.info(f"No blog source for {company.name}")
        return 0

    blog_url = company.sources["blog"]
    if not blog_url:
        logger.info(f"Empty blog URL for {company.name}")
        return 0

    try:
        # Parse RSS feed
        feed = feedparser.parse(blog_url)

        if feed.bozo:
            logger.warning(f"Error parsing RSS feed for {company.name}: {feed.bozo_exception}")
            return 0

        if not feed.entries:
            logger.info(f"No entries found in RSS feed for {company.name}")
            return 0

        new_items = 0
        market_context = ", ".join(company.market_tags[:3])  # First 3 tags for context

        # Process last 10 entries
        for entry in feed.entries[:10]:
            try:
                # Check if already exists
                source_url = entry.get("link", "")
                if not source_url:
                    continue

                existing = db.query(IntelligenceItem).filter(
                    IntelligenceItem.source_url == source_url
                ).first()

                if existing:
                    continue  # Skip duplicates

                if is_duplicate_title(db, company.id, entry.get("title", "Untitled")):
                    continue

                # Extract content
                title = entry.get("title", "Untitled")
                content = entry.get("summary", "") or entry.get("description", "")

                # Parse published date
                published_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published_date = datetime(*entry.published_parsed[:6])
                    except Exception:
                        pass

                # Calculate relevance
                relevance_score = calculate_relevance_score(
                    content, company.market_tags, company.competitors
                )

                # Only process if relevant (score > 0.1)
                if relevance_score < 0.1:
                    logger.debug(f"Skipping low relevance item: {title}")
                    continue

                # Generate AI summary and classification
                summary = summarize_content(content, company.name, market_context)
                category = classify_content(content, company.name)

                # Create intelligence item
                intelligence_item = IntelligenceItem(
                    company_id=company.id,
                    title=title,
                    summary=summary,
                    full_content=content,
                    source_type="blog",
                    source_url=source_url,
                    result_category=category,
                    published_date=published_date,
                    relevance_score=relevance_score,
                    is_read=False,
                    metadata={"feed_title": feed.feed.get("title", "")}
                )

                db.add(intelligence_item)
                new_items += 1

            except Exception as e:
                logger.error(f"Error processing entry for {company.name}: {e}")
                continue

        # Commit all new items
        if new_items > 0:
            db.commit()
            logger.info(f"Added {new_items} new intelligence items for {company.name}")

        return new_items

    except Exception as e:
        logger.error(f"Error scraping blog for {company.name}: {e}")
        db.rollback()
        return 0

