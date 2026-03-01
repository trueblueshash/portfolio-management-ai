from app.db.session import SessionLocal
from app.models.document import PortfolioDocument
from app.services.gdocs_service import extract_google_doc_content
from app.services.document_processor import chunk_text

db = SessionLocal()

# Get the Aug'25 document
doc = db.query(PortfolioDocument).filter(
    PortfolioDocument.google_doc_id == '1xAxF47es_kGlWqXcPrd8k1B5CN8l54rC8mA5xXBegUk'
).first()

if doc:
    print(f"Document: {doc.title}")
    print(f"Full text length: {len(doc.full_text or '')}")
    print(f"Is primary source: {doc.is_primary_source}")
    print(f"MIME type: {doc.mime_type}")
    print()
    
    # Test if text is in database
    if doc.full_text:
        print("Testing chunk_text with database text:")
        chunks = chunk_text(doc.full_text)
        print(f"  Result: {len(chunks)} chunks\n")
    
    # Test fresh extraction
    print("Testing with fresh extraction:")
    doc_content = extract_google_doc_content(doc.google_doc_id)
    fresh_text = doc_content.get('full_text', '')
    print(f"  Fresh text length: {len(fresh_text)}")
    
    chunks = chunk_text(fresh_text)
    print(f"  Result: {len(chunks)} chunks\n")
    
    # Check if it's taking the structured chunking path
    sections = doc_content.get('sections', [])
    print(f"Sections found: {len(sections)}")
    print(f"Is taking structured path: {doc.mime_type == 'application/vnd.google-apps.document' and doc.is_primary_source}")

db.close()