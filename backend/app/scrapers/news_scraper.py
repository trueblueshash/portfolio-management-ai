"""
Google News scraper for monitoring company, competitors, and market tags.
"""
import logging
import feedparser
import requests
import time
import urllib3
from datetime import datetime, timedelta
from typing import List
from urllib.parse import quote
from bs4 import BeautifulSoup
from app.scrapers.base_scraper import BaseScraper
from app.models.company import Company
from sqlalchemy.orm import Session

# Suppress SSL warnings when using verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class NewsScraper(BaseScraper):
    """Scrape Google News RSS feeds"""
    
    def get_source_type(self) -> str:
        return "news"
    
    def scrape(self) -> int:
        """Scrape Google News for company, competitors, and market tags"""
        new_items = 0
        
        # Build search queries
        search_queries = [self.company.name]
        search_queries.extend(self.company.competitors[:5])  # Limit to 5 competitors
        search_queries.extend(self.company.market_tags[:3])  # Limit to 3 market tags
        
        for query in search_queries:
            try:
                items = self._scrape_google_news(query)
                for item in items:
                    if self.save_item(
                        title=item["title"],
                        content=item["content"],
                        source_url=item["url"],
                        published_date=item.get("published_date"),
                        extra_data={"search_query": query, "source": "google_news"}
                    ):
                        new_items += 1
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Error scraping Google News for '{query}': {e}")
                continue
        
        return new_items
    
    def _scrape_google_news(self, query: str) -> List[dict]:
        """Scrape Google News RSS feed for a query"""
        # URL-encode the query to handle spaces and special characters
        encoded_query = quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        
        try:
            # Use requests to fetch RSS feed (bypasses SSL verification)
            response = requests.get(
                rss_url,
                verify=False,  # Bypass SSL verification
                timeout=10,
                headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
            )
            response.raise_for_status()
            
            # Parse the RSS content
            feed = feedparser.parse(response.content)
            
            if feed.bozo:
                logger.warning(f"⚠️  Error parsing Google News RSS for '{query}': {feed.bozo_exception}")
                return []
            
            if not feed.entries:
                logger.debug(f"📰 No news found for '{query}'")
                return []
            
            items = []
            cutoff_date = datetime.now() - timedelta(days=30)  # Last 30 days only
            
            for entry in feed.entries[:20]:  # Limit to 20 most recent
                try:
                    # Parse published date
                    published_date = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            published_date = datetime(*entry.published_parsed[:6])
                            # Skip if too old
                            if published_date < cutoff_date:
                                continue
                        except Exception:
                            pass
                    
                    # Get content
                    title = entry.get("title", "Untitled")
                    link = entry.get("link", "")
                    
                    # Try to get full content from article
                    content = entry.get("summary", "") or entry.get("description", "")
                    
                    # Try to fetch full article content
                    try:
                        full_content = self._fetch_article_content(link)
                        if full_content and len(full_content) > len(content):
                            content = full_content
                    except Exception as e:
                        logger.debug(f"Could not fetch full content from {link}: {e}")
                    
                    if not content or len(content) < 100:
                        continue
                    
                    items.append({
                        "title": title,
                        "content": content,
                        "url": link,
                        "published_date": published_date
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing news entry: {e}")
                    continue
            
            return items
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️  Error fetching Google News for '{query}': {e}")
            return []
        except Exception as e:
            # Log specific error types
            error_str = str(e).lower()
            if "ssl" in error_str or "certificate" in error_str:
                logger.warning(f"⚠️  SSL/certificate error fetching Google News for '{query}': {e}")
            elif "url" in error_str or "encoding" in error_str:
                logger.error(f"❌ URL/encoding error for Google News query '{query}': {e}")
            else:
                logger.error(f"❌ Error fetching Google News RSS for '{query}': {e}")
            return []
    
    def _fetch_article_content(self, url: str) -> str:
        """Fetch and extract article content from URL"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try to find main content
            content_selectors = [
                "article",
                ".article-content",
                ".post-content",
                "main",
                ".content",
                "#content"
            ]
            
            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = " ".join([elem.get_text(strip=True) for elem in elements])
                    if len(content) > 500:
                        break
            
            # Fallback: get all paragraph text
            if not content or len(content) < 500:
                paragraphs = soup.find_all("p")
                content = " ".join([p.get_text(strip=True) for p in paragraphs])
            
            return content[:5000]  # Limit to 5000 chars
            
        except Exception as e:
            logger.debug(f"Could not fetch article content: {e}")
            return ""

