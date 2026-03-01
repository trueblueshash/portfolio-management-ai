"""
Base scraper class with common functionality for all scrapers.
Provides deduplication, AI relevance filtering, and database saving.
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.company import Company
from app.models.intelligence import IntelligenceItem
from app.services.relevance_filter import check_relevance

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all scrapers"""
    
    def __init__(self, db: Session, company: Company):
        self.db = db
        self.company = company
        self.source_type = self.get_source_type()
    
    @abstractmethod
    def get_source_type(self) -> str:
        """Return the source type identifier (e.g., 'blog', 'news', 'reddit')"""
        pass
    
    @abstractmethod
    def scrape(self) -> int:
        """
        Main scraping method. Should return number of new items added.
        Implementations should call save_item() for each relevant item.
        """
        pass
    
    def save_item(
        self,
        title: str,
        content: str,
        source_url: str,
        published_date: Optional[datetime] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save an intelligence item to database after checking:
        1. Deduplication (source_url)
        2. AI relevance filtering
        3. Minimum content length
        
        Returns True if item was saved, False otherwise.
        """
        # Check for duplicates
        existing = self.db.query(IntelligenceItem).filter(
            IntelligenceItem.source_url == source_url
        ).first()
        
        if existing:
            logger.debug(f"⏭️  Skipping duplicate: {source_url}")
            return False
        
        # Check minimum content length
        if not content or len(content.strip()) < 100:
            logger.debug(f"⏭️  Skipping: Content too short ({len(content) if content else 0} chars)")
            return False
        
        # Check date filter (only last 60 days)
        if published_date:
            days_ago = (datetime.now(published_date.tzinfo) - published_date).days
            if days_ago > 60:
                logger.debug(f"⏭️  Skipping: Too old ({days_ago} days ago)")
                return False
        
        # AI relevance check
        try:
            relevance_result = check_relevance(
                content=content,
                title=title,
                company_name=self.company.name,
                market_tags=self.company.market_tags
            )
            
            if not relevance_result["is_relevant"]:
                logger.info(f"❌ Rejected by AI: {title[:50]}... Reason: {relevance_result.get('reason', 'Not relevant')}")
                return False
            
            # Create intelligence item
            intelligence_item = IntelligenceItem(
                company_id=self.company.id,
                title=title,
                summary=relevance_result.get("summary", ""),
                full_content=content,
                source_type=self.source_type,
                source_url=source_url,
                result_category=relevance_result.get("category", "corporate"),
                published_date=published_date,
                relevance_score=relevance_result.get("relevance_score", 0.5),
                is_read=False,
                extra_data=extra_data or {}
            )
            
            self.db.add(intelligence_item)
            
            # Handle duplicate key violations
            try:
                self.db.flush()  # Write immediately to catch duplicates
            except Exception as dup_error:
                if "duplicate key" in str(dup_error).lower() or "unique constraint" in str(dup_error).lower():
                    logger.debug(f"⏭️  Duplicate caught: {source_url}")
                    self.db.rollback()
                    return False
                raise
            
            logger.info(f"✅ Saved: {title[:50]}... (score: {relevance_result.get('relevance_score', 0.5):.2f})")
            return True
            
        except Exception as e:
            logger.error(f"❌ AI relevance check failed for '{title[:50]}...': {e}")
            return False  # Don't save without AI verification

