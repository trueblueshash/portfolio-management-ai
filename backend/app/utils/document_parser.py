"""
Utility functions for parsing document titles and extracting metadata.
"""
import re
from datetime import datetime, date
from typing import Dict, Optional


MONTH_NAMES = {
    'jan': 1, 'january': 1,
    'feb': 2, 'february': 2,
    'mar': 3, 'march': 3,
    'apr': 4, 'april': 4,
    'may': 5,
    'jun': 6, 'june': 6,
    'jul': 7, 'july': 7,
    'aug': 8, 'august': 8,
    'sep': 9, 'september': 9,
    'oct': 10, 'october': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12,
}

QUARTER_MONTHS = {
    'q1': 1, 'q2': 4, 'q3': 7, 'q4': 10,
    '1q': 1, '2q': 4, '3q': 7, '4q': 10,
}


def parse_document_date(title: str) -> Optional[date]:
    """
    Extract document date from title.
    
    Supports patterns:
    - "Dec'25", "Aug'25", "Nov'25" -> 2025-12-01, 2025-08-01, 2025-11-01
    - "December 2025", "August 2025" -> 2025-12-01, 2025-08-01
    - "Q3'26", "Q4'25" -> 2026-07-01, 2025-10-01
    - "2025-12", "2025-08" -> 2025-12-01, 2025-08-01
    
    Returns date object or None if not found.
    """
    title_lower = title.lower()
    
    # Pattern 1: "Dec'25", "Aug'25", "Nov'25"
    match = re.search(r"([a-z]{3})'?(\d{2})", title_lower)
    if match:
        month_name = match.group(1)
        year_suffix = match.group(2)
        if month_name in MONTH_NAMES:
            month = MONTH_NAMES[month_name]
            # Convert 2-digit year to 4-digit (assume 2000s)
            year = 2000 + int(year_suffix)
            if year > 2050:  # If it's clearly in the past, adjust
                year = 1900 + int(year_suffix)
            try:
                return date(year, month, 1)
            except ValueError:
                pass
    
    # Pattern 2: "December 2025", "August 2025"
    match = re.search(r"([a-z]+)\s+(\d{4})", title_lower)
    if match:
        month_name = match.group(1)
        year = int(match.group(2))
        if month_name in MONTH_NAMES:
            month = MONTH_NAMES[month_name]
            try:
                return date(year, month, 1)
            except ValueError:
                pass
    
    # Pattern 3: "Q3'26", "Q4'25"
    match = re.search(r"q([1-4])'?(\d{2})", title_lower)
    if match:
        quarter = int(match.group(1))
        year_suffix = match.group(2)
        year = 2000 + int(year_suffix)
        if year > 2050:
            year = 1900 + int(year_suffix)
        month = QUARTER_MONTHS.get(f'q{quarter}')
        if month:
            try:
                return date(year, month, 1)
            except ValueError:
                pass
    
    # Pattern 4: "2025-12", "2025-08"
    match = re.search(r"(\d{4})-(\d{1,2})", title)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        if 1 <= month <= 12:
            try:
                return date(year, month, 1)
            except ValueError:
                pass
    
    # Default: use current date if nothing found
    return date.today()


def parse_document_type(title: str) -> str:
    """
    Extract document type from title keywords.
    
    Returns:
    - "board_meeting" for "board meeting", "board_update", "board meeting notes"
    - "portfolio_review" for "portfolio review", "portfolio update"
    - "annual_operating_plan" for "AOP", "annual operating plan"
    - "quarterly_review" for "quarterly review", "quarterly update"
    - "update" as default
    """
    title_lower = title.lower()
    
    # Board meeting patterns
    if any(keyword in title_lower for keyword in ['board meeting', 'board_update', 'board notes', 'board deck']):
        return 'board_meeting'
    
    # Portfolio review patterns
    if any(keyword in title_lower for keyword in ['portfolio review', 'portfolio update']):
        return 'portfolio_review'
    
    # Annual operating plan
    if any(keyword in title_lower for keyword in ['aop', 'annual operating plan', 'annual plan']):
        return 'annual_operating_plan'
    
    # Quarterly review
    if any(keyword in title_lower for keyword in ['quarterly review', 'quarterly update', 'q1', 'q2', 'q3', 'q4']):
        return 'quarterly_review'
    
    # IC memo
    if 'ic memo' in title_lower or 'investment committee' in title_lower:
        return 'ic_memo'
    
    # Diligence
    if 'diligence' in title_lower or 'dd' in title_lower:
        return 'diligence'
    
    # Default
    return 'update'


def parse_document_metadata(title: str) -> Dict[str, any]:
    """
    Parse document title to extract metadata.
    
    Returns:
    {
        "document_date": date,  # Parsed date or today
        "doc_type": str,        # Document type
        "title": str            # Original title
    }
    """
    document_date = parse_document_date(title)
    doc_type = parse_document_type(title)
    
    return {
        "document_date": document_date,
        "doc_type": doc_type,
        "title": title
    }

