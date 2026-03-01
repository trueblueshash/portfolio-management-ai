from app.db.session import SessionLocal
from app.models.document import PortfolioDocument, DocumentChunk
from app.services.document_processor import process_document
import logging

logging.basicConfig(level=logging.INFO)

db = SessionLocal()

# Get the Acceldata Google Doc by google_doc_id
doc = db.query(PortfolioDocument).filter(
    PortfolioDocument.google_doc_id == '1mn_Zryn4XiXonQScIM3o3CcTXOUKVrfyJGu3r4czjkM'
).first()

if doc:
    print(f"\n📄 Found: {doc.title}")
    print(f"   ID: {doc.id}")
    print(f"   Processed: {doc.is_processed}")
    print(f"\n🔄 Reprocessing...\n")
    
    try:
        # Pass both document_id AND db session
        process_document(str(doc.id), db)
        
        # Refresh document to get latest state
        db.refresh(doc)
        
        # Check chunks created
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == doc.id
        ).all()
        
        print(f"\n✅ Success!")
        print(f"📊 Created {len(chunks)} chunks")
        print(f"   Processed: {doc.is_processed}")
        print(f"   Summary: {doc.summary[:100] if doc.summary else 'None'}...")
        
        # Show chunk breakdown by section
        from collections import Counter
        sections = Counter([c.source_section for c in chunks if c.source_section])
        if sections:
            print(f"\nChunks by section:")
            for section, count in sorted(sections.items()):
                print(f"  {section}: {count} chunks")
        else:
            print("\n⚠️  No chunks with source_section found")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
else:
    print("❌ Document not found")

db.close()