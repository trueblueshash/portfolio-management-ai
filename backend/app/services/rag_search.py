"""
Enhanced RAG search service with prioritization for hybrid document system.

Prioritizes:
1. Primary Google Docs (is_primary_source=True) - Most recent sections
2. Reference uploads (if no good matches in primary)
3. Archived documents (last resort)
"""
import logging
from typing import List, Optional, Dict, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.document import PortfolioDocument, DocumentChunk
from app.models.company import Company
from app.services.document_processor import generate_embedding
from app.services.relevance_filter import client

logger = logging.getLogger(__name__)


def extract_temporal_context(question: str) -> Dict:
    """
    Detect time references in questions.
    
    Examples:
    - "What's the current ARR?" → search_filter: latest section only
    - "How did ARR trend over 2025?" → search_filter: all 2025 sections
    - "What were Q2 challenges?" → search_filter: Aug'25 section
    """
    question_lower = question.lower()
    
    # Detect "current", "latest", "now", "recent"
    if any(word in question_lower for word in ["current", "latest", "now", "recent", "today"]):
        return {
            "time_filter": "latest",
            "sections": None  # Will filter to most recent section
        }
    
    # Detect quarters
    quarter_map = {
        "q1": ["jan", "feb", "mar", "may'25"],
        "q2": ["apr", "may", "jun", "aug'25"],
        "q3": ["jul", "aug", "sep", "nov'25"],
        "q4": ["oct", "nov", "dec", "dec'25", "feb'26"]
    }
    
    for quarter, months in quarter_map.items():
        if quarter in question_lower:
            return {
                "time_filter": "quarter",
                "quarter": quarter,
                "sections": months
            }
    
    # Detect specific months
    month_patterns = {
        "nov'25": ["nov", "november"],
        "dec'25": ["dec", "december"],
        "aug'25": ["aug", "august"],
        "may'25": ["may"]
    }
    
    for section, patterns in month_patterns.items():
        if any(pattern in question_lower for pattern in patterns):
            return {
                "time_filter": "specific",
                "section": section
            }
    
    # Detect year references
    if "2025" in question or "2024" in question:
        year = "2025" if "2025" in question else "2024"
        return {
            "time_filter": "year",
            "year": year
        }
    
    # Default: search all
    return {
        "time_filter": "all",
        "sections": None
    }


def search_with_priority(
    query: str,
    company_id: Optional[UUID] = None,
    search_scope: str = "primary_only",
    db: Optional[Session] = None
) -> List[Tuple[DocumentChunk, PortfolioDocument, Optional[str]]]:
    """
    Search with intelligent prioritization.
    
    Priority:
    1. Primary Google Docs (is_primary_source=True) - Most recent sections
    2. Reference uploads (if no good matches in primary)
    3. Archived documents (last resort)
    
    Returns:
    List of (chunk, document, company_name) tuples sorted by relevance
    """
    from app.db.session import SessionLocal
    
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        # Generate query embedding
        query_embedding = generate_embedding(query)
        if not query_embedding:
            logger.error("Failed to generate embedding for query")
            return []
        
        # Extract temporal context
        temporal = extract_temporal_context(query)
        
        # Build search query
        search_query = db.query(DocumentChunk, PortfolioDocument, Company.name)\
            .join(PortfolioDocument, DocumentChunk.document_id == PortfolioDocument.id)\
            .outerjoin(Company, PortfolioDocument.company_id == Company.id)\
            .filter(PortfolioDocument.is_processed == True)
        
        # Apply search scope filter
        if search_scope == "primary_only":
            search_query = search_query.filter(PortfolioDocument.is_primary_source == True)
        elif search_scope == "reference_only":
            search_query = search_query.filter(PortfolioDocument.is_primary_source == False)
        # "all" doesn't filter by source
        
        # Apply company filter
        if company_id:
            search_query = search_query.filter(PortfolioDocument.company_id == company_id)
        
        # Apply temporal filter
        if temporal["time_filter"] == "latest":
            # Get most recent section for each company
            # This is simplified - in production, you'd want more sophisticated logic
            search_query = search_query.order_by(
                PortfolioDocument.updated_at.desc(),
                DocumentChunk.source_section.desc()
            )
        elif temporal["time_filter"] == "specific" and temporal.get("section"):
            search_query = search_query.filter(
                DocumentChunk.source_section == temporal["section"]
            )
        elif temporal["time_filter"] == "quarter" and temporal.get("sections"):
            search_query = search_query.filter(
                DocumentChunk.source_section.in_(temporal["sections"])
            )
        
        # Order by similarity (using pgvector cosine distance)
        # Note: This requires pgvector extension and proper indexing
        search_query = search_query.order_by(
            DocumentChunk.chunk_embedding.cosine_distance(query_embedding)
        ).limit(10)
        
        results = search_query.all()
        
        # Sort by priority: primary sources first, then by similarity
        prioritized_results = []
        primary_results = []
        reference_results = []
        
        for chunk, doc, company_name in results:
            if doc.is_primary_source:
                primary_results.append((chunk, doc, company_name))
            else:
                reference_results.append((chunk, doc, company_name))
        
        # Combine: primary first, then reference
        prioritized_results = primary_results + reference_results
        
        return prioritized_results[:10]  # Return top 10
    
    except Exception as e:
        logger.error(f"Error in search_with_priority: {e}", exc_info=True)
        return []
    finally:
        if should_close:
            db.close()


def answer_question_hybrid(
    question: str,
    company_id: Optional[UUID] = None,
    search_scope: str = "primary_only",
    db: Optional[Session] = None
) -> Dict:
    """
    Answer questions using hybrid sources.
    
    Process:
    1. Detect if question is time-specific ("current", "latest", "Q3")
    2. Search primary Google Doc first
    3. If insufficient context, search reference uploads
    4. Build context from both sources
    5. Generate answer with Claude
    6. Cite sources: "Source: Acceldata Portfolio Update (Nov'25 section)"
    """
    from app.db.session import SessionLocal
    
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        # Try primary sources first
        primary_results = search_with_priority(
            question,
            company_id=company_id,
            search_scope="primary_only",
            db=db
        )
        
        # If not enough results, search reference files
        if len(primary_results) < 3:
            reference_results = search_with_priority(
                question,
                company_id=company_id,
                search_scope="reference_only",
                db=db
            )
            all_results = primary_results + reference_results[:5]  # Limit reference results
        else:
            all_results = primary_results
        
        if not all_results:
            return {
                "answer": "I couldn't find any relevant information in the documents to answer this question.",
                "sources": [],
                "citations": [],
                "confidence": 0.0
            }
        
        # Build context from retrieved chunks
        context = ""
        sources = []
        citations = []
        
        for i, (chunk, doc, company_name) in enumerate(all_results[:5]):  # Top 5 chunks
            source_label = "📄" if doc.is_primary_source else "📎"
            section_info = f" ({chunk.source_section})" if chunk.source_section else ""
            
            context += f"--- Source {i+1} {source_label} {doc.title}{section_info} ---\n"
            context += chunk.chunk_text + "\n\n"
            
            sources.append({
                "document_id": str(doc.id),
                "document_title": doc.title,
                "company_name": company_name,
                "section": chunk.source_section,
                "is_primary_source": doc.is_primary_source,
                "chunk_text": chunk.chunk_text[:200] + "..." if len(chunk.chunk_text) > 200 else chunk.chunk_text
            })
            
            citation_text = doc.title
            if chunk.source_section:
                citation_text += f" ({chunk.source_section} section)"
            citations.append({
                "document_title": citation_text,
                "section": chunk.source_section,
                "is_primary_source": doc.is_primary_source
            })
        
        # Generate answer using Claude
        prompt = f"""You are an AI assistant that answers questions based on the provided context from portfolio company documents.

Question: {question}

Context from documents:
{context}

Instructions:
- Provide a clear, concise answer based on the context
- If the information is not in the context, say so
- Cite specific sources when mentioning numbers or facts
- For time-specific questions, prioritize the most recent information
- Format your answer in clear paragraphs

Answer:"""

        try:
            response = client.chat.completions.create(
                model="anthropic/claude-3.5-haiku",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions about portfolio companies based on provided document context."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1,
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Calculate confidence (simplified: based on number of sources)
            confidence = min(1.0, len(all_results) / 5.0)
            
            return {
                "answer": answer,
                "sources": sources,
                "citations": citations,
                "confidence": confidence
            }
        
        except Exception as e:
            logger.error(f"Error generating answer from LLM: {e}")
            return {
                "answer": "I encountered an error while generating the answer. Please try again.",
                "sources": sources,
                "citations": citations,
                "confidence": 0.0
            }
    
    except Exception as e:
        logger.error(f"Error in answer_question_hybrid: {e}", exc_info=True)
        return {
            "answer": "I encountered an error while processing your question. Please try again.",
            "sources": [],
            "citations": [],
            "confidence": 0.0
        }
    finally:
        if should_close:
            db.close()

