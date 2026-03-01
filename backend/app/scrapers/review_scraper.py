"""
Review site scraper - now uses G2Scraper for G2 reviews.
This file is kept for backward compatibility but delegates to G2Scraper.
"""
import logging
from app.scrapers.base_scraper import BaseScraper
from app.scrapers.g2_scraper import G2Scraper

logger = logging.getLogger(__name__)


class ReviewScraper(BaseScraper):
    """Scrape review sites - delegates to G2Scraper for G2 reviews"""
    
    def get_source_type(self) -> str:
        return "review"
    
    def scrape(self) -> int:
        """Scrape review sites - uses G2Scraper for G2"""
        # Delegate to G2Scraper which uses Playwright
        g2_scraper = G2Scraper(self.db, self.company)
        return g2_scraper.scrape()

