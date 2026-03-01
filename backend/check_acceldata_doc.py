from app.db.session import SessionLocal
from app.models.document import PortfolioDocument
from app.models.company import Company

db = SessionLocal()

# Find Acceldata company
company = db.query(Company).filter(Company.name == 'Acceldata').first()

if company:
    print(f"✅ Company: {company.name}")
    print(f"   ID: {company.id}")
    print(f"   Google Doc ID: {company.primary_gdoc_id}")
    print(f"   Sync enabled: {company.gdoc_sync_enabled}")
    print()
else:
    print("❌ Acceldata company not found!")
    print("\nAll companies:")
    all_companies = db.query(Company).all()
    for c in all_companies:
        print(f"  - {c.name}")

# Find ALL documents
all_docs = db.query(PortfolioDocument).all()
print(f"\n📄 Total documents in database: {len(all_docs)}")

if company:
    # Find Acceldata documents
    docs = db.query(PortfolioDocument).filter(
        PortfolioDocument.company_id == company.id
    ).all()
    
    print(f"📄 Acceldata documents: {len(docs)}")
    for doc in docs:
        print(f"\n   Title: {doc.title}")
        print(f"   ID: {doc.id}")
        print(f"   Google Doc ID: {doc.google_doc_id}")
        print(f"   MIME Type: {doc.mime_type}")
        print(f"   Is Primary: {doc.is_primary_source}")
        print(f"   Processed: {doc.is_processed}")

db.close()