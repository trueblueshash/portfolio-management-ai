#!/usr/bin/env python3
"""
Master orchestrator script for comprehensive intelligence gathering.
Runs all scrapers for one or all portfolio companies.

Usage:
    python run_comprehensive_scrapers.py              # All companies
    python run_comprehensive_scrapers.py Acceldata    # Single company
"""
import sys
import logging
from datetime import datetime
from app.db.session import SessionLocal
from app.models.company import Company
from app.scrapers.company_content import CompanyContentScraper
from app.scrapers.news_scraper import NewsScraper
from app.scrapers.competitor_monitor import CompetitorMonitor
from app.scrapers.reddit_scraper import RedditScraper
# from app.scrapers.review_scraper import ReviewScraper  # Disabled - G2 blocks automated scraping

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def run_scrapers_for_company(db, company):
    """Run all scrapers for a single company"""
    logger.info(f"\n{'='*60}")
    logger.info(f"🏢 Processing: {company.name}")
    logger.info(f"{'='*60}")
    
    total_new = 0
    scraper_results = {}
    
    # Note: G2 review scraping is disabled due to anti-bot protection.
    # G2 reviews can be monitored manually or via paid services like Apify.
    # The 4 active scrapers provide comprehensive intelligence coverage.
    
    # 1. Company's own content (blog, newsroom, case studies)
    try:
        logger.info("📝 Scraping company content (blog, newsroom, case studies)...")
        scraper = CompanyContentScraper(db, company)
        new_items = scraper.scrape()
        scraper_results["Company Content"] = new_items
        total_new += new_items
        db.commit()  # Commit after each scraper
        logger.info(f"   ✅ Found {new_items} new items (committed)")
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        db.rollback()
        scraper_results["Company Content"] = 0
    
    # 2. Google News (company + competitors + market tags)
    try:
        logger.info("📰 Scraping Google News...")
        scraper = NewsScraper(db, company)
        new_items = scraper.scrape()
        scraper_results["Google News"] = new_items
        total_new += new_items
        db.commit()  # Commit after each scraper
        logger.info(f"   ✅ Found {new_items} new items (committed)")
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        db.rollback()
        scraper_results["Google News"] = 0
    
    # 3. Competitor monitoring (competitor blogs and announcements)
    try:
        logger.info("🔍 Monitoring competitors...")
        scraper = CompetitorMonitor(db, company)
        new_items = scraper.scrape()
        scraper_results["Competitors"] = new_items
        total_new += new_items
        db.commit()  # Commit after each scraper
        logger.info(f"   ✅ Found {new_items} new items (committed)")
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        db.rollback()
        scraper_results["Competitors"] = 0
    
    # 4. Reddit (community discussions)
    try:
        logger.info("💬 Scraping Reddit discussions...")
        scraper = RedditScraper(db, company)
        new_items = scraper.scrape()
        scraper_results["Reddit"] = new_items
        total_new += new_items
        db.commit()  # Commit after each scraper
        logger.info(f"   ✅ Found {new_items} new items (committed)")
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        db.rollback()
        scraper_results["Reddit"] = 0
    
    # 5. Review sites (G2) - DISABLED: G2 blocks automated scraping
    # Note: G2 review scraping is disabled due to anti-bot protection.
    # G2 reviews can be monitored manually or via paid services like Apify.
    # The 4 active scrapers provide comprehensive intelligence coverage.
    # try:
    #     logger.info("⭐ Scraping review sites (G2, etc.)...")
    #     scraper = ReviewScraper(db, company)
    #     new_items = scraper.scrape()
    #     scraper_results["Reviews"] = new_items
    #     total_new += new_items
    #     db.commit()  # Commit after each scraper
    #     if new_items > 0:
    #         logger.info(f"   ✅ Found {new_items} new items (committed)")
    #     else:
    #         logger.info(f"   ⚠️  No items found (may require JS rendering)")
    # except Exception as e:
    #     logger.error(f"   ❌ Error: {e}")
    #     db.rollback()
    #     scraper_results["Reviews"] = 0
    
    # Final commit to ensure all items are saved
    try:
        db.commit()
        logger.info(f"\n✅ Successfully committed all {total_new} items to database")
    except Exception as e:
        logger.error(f"❌ Error committing to database: {e}")
        db.rollback()
    
    # Summary
    logger.info(f"\n📊 Summary for {company.name}:")
    for scraper_name, count in scraper_results.items():
        logger.info(f"   {scraper_name}: {count} items")
    logger.info(f"   TOTAL: {total_new} new items\n")
    
    return total_new


def main():
    """Main entry point"""
    company_name = sys.argv[1] if len(sys.argv) > 1 else None
    
    logger.info("="*60)
    logger.info("🚀 Portfolio Intelligence Gathering System")
    logger.info("="*60)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    db = SessionLocal()
    try:
        if company_name:
            # Single company
            company = db.query(Company).filter(Company.name.ilike(f"%{company_name}%")).first()
            if not company:
                logger.error(f"❌ Company '{company_name}' not found!")
                return
            
            total = run_scrapers_for_company(db, company)
            logger.info(f"\n🎉 Complete! Total new items: {total}")
            
        else:
            # All companies
            companies = db.query(Company).all()
            logger.info(f"📋 Processing {len(companies)} companies...\n")
            
            grand_total = 0
            company_totals = {}
            
            for company in companies:
                try:
                    new_items = run_scrapers_for_company(db, company)
                    company_totals[company.name] = new_items
                    grand_total += new_items
                except Exception as e:
                    logger.error(f"❌ Fatal error processing {company.name}: {e}")
                    company_totals[company.name] = 0
                    continue
            
            # Final summary
            logger.info("\n" + "="*60)
            logger.info("📊 FINAL SUMMARY")
            logger.info("="*60)
            for company_name, count in sorted(company_totals.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"   {company_name}: {count} items")
            logger.info(f"\n   GRAND TOTAL: {grand_total} new items")
            logger.info(f"\n✅ All companies processed!")
            logger.info(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()

