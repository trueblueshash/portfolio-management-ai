"""
Google Docs API integration service for syncing portfolio company documents.

Setup Instructions:
1. Create Google Cloud Project
2. Enable Google Docs API
3. Create Service Account
4. Download credentials JSON
5. Share Google Docs with service account email
6. Add to .env: GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/creds.json
"""
import logging
import os
import re
from typing import Dict, List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.company import Company
from app.models.document import PortfolioDocument, DocumentChunk
from app.services.document_processor import generate_embedding, generate_summary, chunk_google_doc_by_structure
from app.utils.document_parser import parse_document_metadata

logger = logging.getLogger(__name__)
settings = get_settings()


def get_google_docs_service():
    """Initialize and return Google Docs API service."""
    credentials_path = settings.GOOGLE_SERVICE_ACCOUNT_JSON
    if not credentials_path:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON environment variable not set")
    
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Google service account credentials not found at: {credentials_path}")
    
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=[
            'https://www.googleapis.com/auth/documents.readonly',
            'https://www.googleapis.com/auth/drive.readonly',
        ]
    )
    
    service = build('docs', 'v1', credentials=credentials)
    return service


def extract_google_doc_id(url: str) -> str:
    """
    Extract Google Doc ID from URL.
    
    Examples:
    - https://docs.google.com/document/d/1mn_Zryn4XiXonQScIM3o3CcTXOUKVrfyJGu3r4czjkM/edit
    - Returns: 1mn_Zryn4XiXonQScIM3o3CcTXOUKVrfyJGu3r4czjkM
    """
    match = re.search(r'/document/d/([a-zA-Z0-9_-]+)', url)
    if not match:
        raise ValueError(f"Invalid Google Doc URL: {url}")
    return match.group(1)


def extract_google_doc_content(doc_id: str) -> Dict:
    """
    Fetch and parse Google Doc content.
    
    Returns:
    {
        "full_text": str,
        "sections": [
            {
                "heading": "Nov'25",
                "content": "...",
                "subsections": {
                    "Summary": "...",
                    "Metrics": {...},
                    "Q&A": [...]
                }
            },
            ...
        ]
    }
    """
    try:
        service = get_google_docs_service()
        doc = service.documents().get(documentId=doc_id).execute()
        
        full_text = ""
        sections = []
        current_section = None
        current_subsection = None
        
        # Parse document structure
        for element in doc.get('body', {}).get('content', []):
            if 'paragraph' in element:
                para = element['paragraph']
                text_elements = para.get('elements', [])
                
                # Check if this is a heading
                heading_style = para.get('paragraphStyle', {}).get('namedStyleType', '')
                is_heading = heading_style.startswith('HEADING')
                
                para_text = ""
                for elem in text_elements:
                    if 'textRun' in elem:
                        para_text += elem['textRun'].get('content', '')
                
                if is_heading and para_text.strip():
                    # New section detected (e.g., "Nov'25", "Dec'25")
                    section_match = re.match(r"([A-Za-z]{3}'?\d{2})", para_text.strip())
                    if section_match:
                        # Save previous section
                        if current_section:
                            sections.append(current_section)
                        
                        # Start new section
                        current_section = {
                            "heading": section_match.group(1),
                            "content": "",
                            "subsections": {}
                        }
                        current_subsection = None
                elif para_text.strip():
                    # Regular paragraph
                    if current_section:
                        current_section["content"] += para_text + "\n"
                    full_text += para_text + "\n"
                    
                    # Detect subsections (Summary, Metrics, Q&A)
                    if re.match(r'^(Summary|Metrics|Q&A|Questions to Ask):', para_text, re.IGNORECASE):
                        subsection_name = re.match(r'^([^:]+):', para_text, re.IGNORECASE).group(1)
                        current_subsection = subsection_name
                        if current_section:
                            current_section["subsections"][subsection_name] = ""
                    elif current_subsection and current_section:
                        # Append to current subsection
                        current_section["subsections"][current_subsection] += para_text + "\n"
        
        # Add last section
        if current_section:
            sections.append(current_section)
        
        return {
            "full_text": full_text.strip(),
            "sections": sections
        }
    
    except HttpError as e:
        logger.error(f"Error fetching Google Doc {doc_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching Google Doc {doc_id}: {e}")
        raise


def parse_google_doc_structure(doc_content: Dict) -> Dict:
    """
    Parse Google Doc content into structured sections.
    
    Returns same structure as extract_google_doc_content but with additional metadata.
    """
    return doc_content


def sync_single_google_doc(document: PortfolioDocument, db: Session) -> Dict:
    """
    Sync a single Google Doc document.
    
    Process:
    1. Fetch latest content from Google Docs API
    2. Update full_text
    3. Intelligent chunking by section (Nov'25, Dec'25, etc.)
    4. Generate embeddings for each section
    5. Update document_chunks (delete old, insert new)
    6. Generate/update summary
    
    Returns:
    {
        "status": "success" | "no_changes",
        "chunks_created": int,
        "document_id": str
    }
    """
    if not document.google_doc_id:
        raise ValueError(f"Document {document.id} has no google_doc_id")
    
    logger.info(f"Syncing Google Doc: {document.title} (Doc ID: {document.google_doc_id})")
    
    # Fetch content from Google Docs API
    doc_content = extract_google_doc_content(document.google_doc_id)
    parsed_structure = parse_google_doc_structure(doc_content)
    
    # Check if content changed
    if document.full_text == doc_content["full_text"]:
        logger.info(f"No changes detected for {document.title}")
        return {
            "status": "no_changes",
            "chunks_created": 0,
            "document_id": str(document.id)
        }
    
    # Update document content
    document.full_text = doc_content["full_text"]
    document.updated_at = datetime.now()
    
    # Delete old chunks
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
    
    # Generate chunks using structured chunking
    structured_chunks = chunk_google_doc_by_structure(doc_content, parsed_structure["sections"])
    chunks_created = 0
    
    for idx, (chunk_text, source_section, metadata) in enumerate(structured_chunks):
        embedding = generate_embedding(chunk_text)
        
        chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=idx,
            chunk_text=chunk_text,
            chunk_embedding=embedding,
            source_section=source_section
        )
        db.add(chunk)
        chunks_created += 1
    
    # Generate summary
    company_name = document.company.name if document.company else None
    document.summary = generate_summary(doc_content["full_text"], company_name)
    
    # Mark as processed
    document.is_processed = True
    
    db.commit()
    
    logger.info(f"✅ Successfully synced {document.title}: {chunks_created} chunks created")
    
    return {
        "status": "success",
        "chunks_created": chunks_created,
        "document_id": str(document.id)
    }


def sync_company_google_doc(company_id: UUID, db: Optional[Session] = None) -> Dict:
    """
    Sync ALL active Google Docs for a company.
    
    Process:
    1. Find all active PortfolioDocument records for company (is_active=True, google_doc_id is not null)
    2. Sync each document
    3. Update company.gdoc_last_synced
    
    Returns:
    {
        "status": "success",
        "documents_synced": int,
        "total_chunks_created": int,
        "last_synced": datetime
    }
    """
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company not found: {company_id}")
        
        # Find all active Google Docs for this company
        documents = db.query(PortfolioDocument).filter(
            PortfolioDocument.company_id == company_id,
            PortfolioDocument.google_doc_id.isnot(None),
            PortfolioDocument.is_active == True
        ).all()
        
        if not documents:
            logger.warning(f"Company {company.name} has no active Google Docs to sync")
            return {
                "status": "no_documents",
                "documents_synced": 0,
                "total_chunks_created": 0,
                "last_synced": company.gdoc_last_synced
            }
        
        logger.info(f"Syncing {len(documents)} Google Doc(s) for {company.name}")
        
        documents_synced = 0
        total_chunks_created = 0
        errors = []
        
        for document in documents:
            try:
                result = sync_single_google_doc(document, db)
                if result["status"] == "success":
                    documents_synced += 1
                    total_chunks_created += result["chunks_created"]
            except Exception as e:
                logger.error(f"Error syncing document {document.id}: {e}", exc_info=True)
                errors.append({
                    "document_id": str(document.id),
                    "title": document.title,
                    "error": str(e)
                })
        
        # Update company sync timestamp
        company.gdoc_last_synced = datetime.now()
        db.commit()
        
        logger.info(f"✅ Synced {documents_synced}/{len(documents)} documents for {company.name}")
        
        return {
            "status": "success",
            "documents_synced": documents_synced,
            "total_chunks_created": total_chunks_created,
            "last_synced": company.gdoc_last_synced,
            "errors": errors if errors else None
        }
    
    except Exception as e:
        logger.error(f"Error syncing Google Docs for company {company_id}: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        if should_close:
            db.close()


def sync_all_enabled_google_docs() -> Dict:
    """
    Sync all companies with gdoc_sync_enabled=True.
    Check sync_frequency and only sync if due.
    """
    db = SessionLocal()
    try:
        companies = db.query(Company).filter(
            Company.gdoc_sync_enabled == True
        ).all()
        
        results = {
            "total_companies": len(companies),
            "synced": 0,
            "skipped": 0,
            "failed": 0,
            "errors": []
        }
        
        for company in companies:
            # Check if sync is due
            if company.gdoc_last_synced:
                time_since_sync = datetime.now() - company.gdoc_last_synced
                sync_interval = timedelta(minutes=company.gdoc_sync_frequency_minutes)
                
                if time_since_sync < sync_interval:
                    logger.debug(f"Skipping {company.name} - sync not due yet")
                    results["skipped"] += 1
                    continue
            
            try:
                sync_company_google_doc(company.id, db)
                results["synced"] += 1
            except Exception as e:
                logger.error(f"Failed to sync {company.name}: {e}")
                results["failed"] += 1
                results["errors"].append({
                    "company": company.name,
                    "error": str(e)
                })
        
        return results
    
    finally:
        db.close()
