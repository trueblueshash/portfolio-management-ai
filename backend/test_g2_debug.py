#!/usr/bin/env python3
print("🔍 Starting G2 debug script...")

import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')

print("Loading modules...")
from app.db.session import SessionLocal
from app.models.company import Company
from app.scrapers.g2_scraper import G2Scraper

print("✅ Modules loaded\n")

db = SessionLocal()
company = db.query(Company).filter(Company.name == "Acceldata").first()

if company:
    print(f"🎯 Testing G2 scraper for: {company.name}")
    print(f"Competitors: {company.competitors[:3]}\n")
    
    try:
        scraper = G2Scraper(db, company)
        print("Starting scrape...\n")
        count = scraper.scrape()
        
        print(f"\n✅ Scrape complete: {count} items found")
        db.commit()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
else:
    print("❌ Acceldata not found")

db.close()
print("\n✅ Done")
