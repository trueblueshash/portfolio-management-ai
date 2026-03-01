from app.services.gdocs_service import get_google_docs_service
import json

file_id = "1mn_Zryn4XiXonQScIM3o3CcTXOUKVrfyJGu3r4czjkM"

try:
    service = get_google_docs_service()
    doc = service.documents().get(documentId=file_id).execute()
    
    print(f"✅ Successfully fetched document!")
    print(f"Title: {doc.get('title')}")
    
    # Check body content
    body_content = doc.get('body', {}).get('content', [])
    print(f"\n📊 Body has {len(body_content)} elements")
    
    # Show ALL elements
    for i, element in enumerate(body_content):
        print(f"\n--- Element {i} ---")
        print(f"Keys: {element.keys()}")
        print(f"Start/End: {element.get('startIndex')} - {element.get('endIndex')}")
        
        if 'paragraph' in element:
            para = element['paragraph']
            print(f"Paragraph style: {para.get('paragraphStyle', {}).get('namedStyleType', 'NORMAL')}")
            
            text_runs = para.get('elements', [])
            print(f"Text runs: {len(text_runs)}")
            
            for j, text_elem in enumerate(text_runs):
                if 'textRun' in text_elem:
                    content = text_elem['textRun'].get('content', '')
                    if content.strip():
                        print(f"  Text run {j}: {repr(content[:200])}")
        
        if 'table' in element:
            print(f"TABLE found with {len(element['table'].get('tableRows', []))} rows")
        
        if 'sectionBreak' in element:
            print("SECTION BREAK")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()