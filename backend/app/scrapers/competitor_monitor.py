"""
Monitor competitor blogs, newsrooms, and LinkedIn for strategic intelligence.
"""
import logging
import feedparser
import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from app.scrapers.base_scraper import BaseScraper
from app.models.company import Company
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CompetitorMonitor(BaseScraper):
    """Monitor competitor activity"""
    
    def get_source_type(self) -> str:
        return "competitor"
    
    def scrape(self) -> int:
        """Monitor all competitors"""
        new_items = 0
        
        for competitor in self.company.competitors[:5]:  # Limit to 5 competitors
            try:
                items = self._scrape_competitor(competitor)
                for item in items:
                    if self.save_item(
                        title=item["title"],
                        content=item["content"],
                        source_url=item["url"],
                        published_date=item.get("published_date"),
                        extra_data={
                            "competitor": competitor,
                            "source": item.get("source", "blog")
                        }
                    ):
                        new_items += 1
                
                # Rate limiting
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"❌ Error monitoring competitor '{competitor}': {e}")
                continue
        
        return new_items
    
    def _scrape_competitor(self, competitor_name: str) -> List[Dict]:
        """Scrape competitor's blog, newsroom, and case studies"""
        items = []
        
        # Try to find competitor's blog/newsroom
        # Common patterns:
        blog_patterns = [
            f"https://www.{competitor_name.lower().replace(' ', '')}.com/blog",
            f"https://www.{competitor_name.lower().replace(' ', '')}.com/news",
            f"https://www.{competitor_name.lower().replace(' ', '')}.com/newsroom",
            f"https://blog.{competitor_name.lower().replace(' ', '')}.com",
        ]
        
        for pattern in blog_patterns:
            try:
                # Try RSS feed
                rss_urls = [
                    f"{pattern}/feed",
                    f"{pattern}/rss",
                    f"{pattern}/rss.xml",
                    f"{pattern}/feed.xml",
                ]
                
                for rss_url in rss_urls:
                    feed_items = self._scrape_rss_feed(rss_url, competitor_name)
                    if feed_items:
                        items.extend(feed_items)
                        break  # Found working RSS feed
                
                # If no RSS, try scraping HTML
                if not items:
                    html_items = self._scrape_html_blog(pattern, competitor_name)
                    if html_items:
                        items.extend(html_items)
                        break
                
            except Exception as e:
                logger.debug(f"Could not scrape {pattern}: {e}")
                continue
        
        return items[:10]  # Limit to 10 items per competitor
    
    def _scrape_rss_feed(self, rss_url: str, competitor_name: str) -> List[Dict]:
        """Scrape RSS feed"""
        try:
            feed = feedparser.parse(rss_url)
            
            if feed.bozo or not feed.entries:
                return []
            
            items = []
            cutoff_date = datetime.now() - timedelta(days=60)
            
            for entry in feed.entries[:10]:
                try:
                    # Parse date
                    published_date = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            published_date = datetime(*entry.published_parsed[:6])
                            if published_date < cutoff_date:
                                continue
                        except Exception:
                            pass
                    
                    title = entry.get("title", "Untitled")
                    link = entry.get("link", "")
                    content = entry.get("summary", "") or entry.get("description", "")
                    
                    if not content or len(content) < 100:
                        continue
                    
                    items.append({
                        "title": f"[{competitor_name}] {title}",
                        "content": content,
                        "url": link,
                        "published_date": published_date,
                        "source": "blog"
                    })
                    
                except Exception as e:
                    logger.debug(f"Error processing RSS entry: {e}")
                    continue
            
            return items
            
        except Exception as e:
            logger.debug(f"Error parsing RSS feed {rss_url}: {e}")
            return []
    
    def _scrape_html_blog(self, blog_url: str, competitor_name: str) -> List[Dict]:
        """Scrape HTML blog page"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(blog_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find article links
            article_links = []
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True)
                
                # Look for article/blog post links
                if any(keyword in href.lower() for keyword in ["/blog/", "/post/", "/article/", "/news/"]):
                    if text and len(text) > 20:
                        full_url = href if href.startswith("http") else f"{blog_url.rstrip('/')}/{href.lstrip('/')}"
                        article_links.append({"url": full_url, "title": text})
            
            # Limit to 5 most recent
            items = []
            for article in article_links[:5]:
                try:
                    # Fetch article content
                    content = self._fetch_article_content(article["url"])
                    if content and len(content) > 100:
                        items.append({
                            "title": f"[{competitor_name}] {article['title']}",
                            "content": content,
                            "url": article["url"],
                            "published_date": None,
                            "source": "blog"
                        })
                except Exception as e:
                    logger.debug(f"Could not fetch article {article['url']}: {e}")
                    continue
            
            return items
            
        except Exception as e:
            logger.debug(f"Error scraping HTML blog {blog_url}: {e}")
            return []
    
    def _fetch_article_content(self, url: str) -> str:
        """Fetch article content"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Remove script and style
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Find main content
            content_selectors = ["article", ".article-content", ".post-content", "main"]
            content = ""
            
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = " ".join([elem.get_text(strip=True) for elem in elements])
                    if len(content) > 500:
                        break
            
            if not content:
                paragraphs = soup.find_all("p")
                content = " ".join([p.get_text(strip=True) for p in paragraphs])
            
            return content[:5000]
            
        except Exception as e:
            logger.debug(f"Could not fetch article content: {e}")
            return ""

