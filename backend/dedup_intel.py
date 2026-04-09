import re
from sqlalchemy import text
from app.db.session import SessionLocal
 
db = SessionLocal()
result = db.execute(text("""
SELECT id, title, source_type, captured_date 
FROM intelligence_items 
WHERE company_id = '1c4c2a24-241d-4535-b143-20803d4a469b'
ORDER BY captured_date ASC
"""))
rows = result.fetchall()
 
def normalize(title):
    title = re.split(r'\s*[-|–]\s*(?=[A-Z][a-z])', title)[0]
    title = re.sub(r'[^\w\s]', '', title.lower())
    return set(title.split())
 
seen = []
to_delete = []
 
for row in rows:
    rid, title, stype, cdate = row
    words = normalize(title or '')
    if len(words) < 3:
        seen.append((rid, title, words))
        continue
    is_dup = False
    for sid, stitle, swords in seen:
        if len(swords) < 3:
            continue
        overlap = len(words & swords)
        smaller = min(len(words), len(swords))
        similarity = overlap / smaller
        if similarity >= 0.45:
            is_dup = True
            to_delete.append(str(rid))
            print(f'DUP: "{title[:60]}" ~= "{stitle[:60]}"')
            break
    if not is_dup:
        seen.append((rid, title, words))
 
print(f"\nFound {len(to_delete)} duplicates")
if to_delete:
    ids = ",".join(["'" + i + "'" for i in to_delete])
    db.execute(text(f"DELETE FROM intelligence_items WHERE id IN ({ids})"))
    db.commit()
    print(f"Deleted {len(to_delete)} duplicates")
else:
    print("No duplicates found")
db.close()
 