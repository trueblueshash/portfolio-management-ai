import re
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.intelligence import IntelligenceItem


def is_duplicate_title(db: Session, company_id, new_title: str, days_back: int = 7) -> bool:
    """Check if a similar title already exists for this company recently."""

    def normalize(title: str):
        title = re.split(r"\s*[-|–]\s*(?=[A-Z][a-z])", title)[0]
        title = re.sub(r"[^\w\s]", "", title.lower())
        return set(title.split())

    new_words = normalize(new_title or "")
    # Short titles: skip duplicate detection (avoids false matches vs longer titles)
    if len(new_words) < 4:
        return False

    cutoff = datetime.utcnow() - timedelta(days=days_back)
    recent_items = db.query(IntelligenceItem).filter(
        IntelligenceItem.company_id == company_id,
        IntelligenceItem.captured_date >= cutoff,
    ).all()

    for item in recent_items:
        existing_words = normalize(item.title or "")
        if len(existing_words) < 4:
            continue
        overlap = len(new_words & existing_words)
        similarity = overlap / max(len(new_words), len(existing_words))
        if similarity >= 0.75:
            return True
    return False
