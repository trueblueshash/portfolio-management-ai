import logging
from celery import Celery
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.company import Company
from app.scrapers.company_content import CompanyContentScraper
from app.scrapers.news_scraper import NewsScraper
from app.scrapers.competitor_monitor import CompetitorMonitor
from app.scrapers.reddit_scraper import RedditScraper
# from app.scrapers.review_scraper import ReviewScraper  # Disabled - G2 blocks automated scraping
from app.services.document_processor import process_document

logger = logging.getLogger(__name__)

celery_app = Celery(
    "portfolio_intelligence",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "scrape-all-companies": {
            "task": "app.core.celery_app.scrape_all_companies",
            "schedule": 1209600.0,  # Every 14 days (14 * 24 * 60 * 60 seconds)
        },
        "sync-google-docs": {
            "task": "app.core.celery_app.sync_all_google_docs",
            "schedule": 3600.0,  # Every 1 hour (60 * 60 seconds)
        },
    },
)


def run_comprehensive_scrapers_for_company(db, company):
    """Run all comprehensive scrapers for a single company"""
    # Note: G2 review scraping is disabled due to anti-bot protection.
    # G2 reviews can be monitored manually or via paid services like Apify.
    # The 4 active scrapers provide comprehensive intelligence coverage.
    
    total_new = 0
    scraper_results = {}
    
    # 1. Company's own content (blog, newsroom, case studies)
    try:
        scraper = CompanyContentScraper(db, company)
        new_items = scraper.scrape()
        scraper_results["company_content"] = new_items
        total_new += new_items
        logger.info(f"Company content: {new_items} items for {company.name}")
    except Exception as e:
        logger.error(f"Error scraping company content for {company.name}: {e}")
        scraper_results["company_content"] = 0
    
    # 2. Google News (company + competitors + market tags)
    try:
        scraper = NewsScraper(db, company)
        new_items = scraper.scrape()
        scraper_results["news"] = new_items
        total_new += new_items
        logger.info(f"Google News: {new_items} items for {company.name}")
    except Exception as e:
        logger.error(f"Error scraping news for {company.name}: {e}")
        scraper_results["news"] = 0
    
    # 3. Competitor monitoring (competitor blogs and announcements)
    try:
        scraper = CompetitorMonitor(db, company)
        new_items = scraper.scrape()
        scraper_results["competitors"] = new_items
        total_new += new_items
        logger.info(f"Competitors: {new_items} items for {company.name}")
    except Exception as e:
        logger.error(f"Error scraping competitors for {company.name}: {e}")
        scraper_results["competitors"] = 0
    
    # 4. Reddit (community discussions)
    try:
        scraper = RedditScraper(db, company)
        new_items = scraper.scrape()
        scraper_results["reddit"] = new_items
        total_new += new_items
        logger.info(f"Reddit: {new_items} items for {company.name}")
    except Exception as e:
        logger.error(f"Error scraping Reddit for {company.name}: {e}")
        scraper_results["reddit"] = 0
    
    # 5. Review sites (G2) - DISABLED: G2 blocks automated scraping
    # Note: G2 review scraping is disabled due to anti-bot protection.
    # G2 reviews can be monitored manually or via paid services like Apify.
    # The 4 active scrapers provide comprehensive intelligence coverage.
    # try:
    #     scraper = ReviewScraper(db, company)
    #     new_items = scraper.scrape()
    #     scraper_results["reviews"] = new_items
    #     total_new += new_items
    #     if new_items > 0:
    #         logger.info(f"Reviews: {new_items} items for {company.name}")
    # except Exception as e:
    #     logger.error(f"Error scraping reviews for {company.name}: {e}")
    #     scraper_results["reviews"] = 0
    
    # Commit all changes
    try:
        db.commit()
    except Exception as e:
        logger.error(f"Error committing to database for {company.name}: {e}")
        db.rollback()
    
    return total_new, scraper_results


@celery_app.task(name="app.core.celery_app.scrape_all_companies")
def scrape_all_companies():
    """Run comprehensive scrapers for all companies"""
    db = SessionLocal()
    try:
        companies = db.query(Company).all()
        grand_total = 0
        company_totals = {}
        
        for company in companies:
            try:
                total_new, _ = run_comprehensive_scrapers_for_company(db, company)
                company_totals[company.name] = total_new
                grand_total += total_new
            except Exception as e:
                logger.error(f"Fatal error processing {company.name}: {e}")
                company_totals[company.name] = 0
        
        logger.info(f"✅ Comprehensive scraping complete: {grand_total} total new items across {len(companies)} companies")
        return {"total_new_items": grand_total, "company_totals": company_totals}
    finally:
        db.close()


@celery_app.task(name="app.core.celery_app.scrape_company")
def scrape_company(company_id: str):
    """Run comprehensive scrapers for a single company"""
    from uuid import UUID
    db = SessionLocal()
    try:
        # Convert string to UUID
        company_uuid = UUID(company_id)
        company = db.query(Company).filter(Company.id == company_uuid).first()
        if not company:
            logger.error(f"Company not found: {company_id}")
            return {"error": "Company not found"}
        
        total_new, scraper_results = run_comprehensive_scrapers_for_company(db, company)
        logger.info(f"✅ Comprehensive scraping complete for {company.name}: {total_new} new items")
        return {
            "company_id": company_id,
            "company_name": company.name,
            "new_items": total_new,
            "scraper_results": scraper_results
        }
    finally:
        db.close()


@celery_app.task(name="app.core.celery_app.process_document_task")
def process_document_task(document_id: str):
    """Process a document in the background"""
    db = SessionLocal()
    try:
        process_document(document_id, db)
        logger.info(f"✅ Document processing complete: {document_id}")
        return {"status": "success", "document_id": document_id}
    except Exception as e:
        logger.error(f"❌ Error processing document {document_id}: {e}")
        return {"status": "error", "document_id": document_id, "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.core.celery_app.sync_all_google_docs")
def sync_all_google_docs():
    """Sync all enabled Google Docs"""
    from app.services.gdocs_service import sync_all_enabled_google_docs
    
    try:
        results = sync_all_enabled_google_docs()
        logger.info(f"✅ Google Docs sync complete: {results['synced']} synced, {results['skipped']} skipped, {results['failed']} failed")
        return results
    except Exception as e:
        logger.error(f"❌ Error syncing Google Docs: {e}")
        return {"status": "error", "error": str(e)}
