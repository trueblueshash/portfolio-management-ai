from app.services.gdocs_service import extract_google_doc_content

file_id = "1mn_Zryn4XiXonQScIM3o3CcTXOUKVrfyJGu3r4czjkM"

doc_content = extract_google_doc_content(file_id)

print(f"Full text length: {len(doc_content.get('full_text', ''))}")
print(f"Number of sections: {len(doc_content.get('sections', []))}")
print(f"\nFirst 500 characters:")
print(doc_content.get('full_text', '')[:500])
print(f"\nSections:")
for section in doc_content.get('sections', []):
    print(f"  - {section.get('heading')}")