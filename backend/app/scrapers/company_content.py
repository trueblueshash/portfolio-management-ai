"""
Scrape company's own content: blog, newsroom, case studies, changelog.
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


class CompanyContentScraper(BaseScraper):
    """Scrape company's own content sources"""
    
    def get_source_type(self) -> str:
        return "company_content"
    
    def scrape(self) -> int:
        """Scrape all company content sources"""
        new_items = 0
        
        sources = self.company.sources or {}
        
        # Scrape blog RSS
        if "blog" in sources and sources["blog"]:
            try:
                items = self._scrape_blog_rss(sources["blog"])
                for item in items:
                    if self.save_item(
                        title=item["title"],
                        content=item["content"],
                        source_url=item["url"],
                        published_date=item.get("published_date"),
                        extra_data={"source": "blog"}
                    ):
                        new_items += 1
            except Exception as e:
                logger.error(f"❌ Error scraping blog: {e}")
        
        # Scrape newsroom/press releases
        newsroom_urls = [
            sources.get("newsroom"),
            sources.get("press"),
            f"{sources.get('blog', '').rstrip('/blog')}/newsroom" if sources.get("blog") else None,
            f"{sources.get('blog', '').rstrip('/blog')}/press" if sources.get("blog") else None,
        ]
        
        for newsroom_url in newsroom_urls:
            if not newsroom_url:
                continue
            try:
                items = self._scrape_newsroom(newsroom_url)
                for item in items:
                    if self.save_item(
                        title=item["title"],
                        content=item["content"],
                        source_url=item["url"],
                        published_date=item.get("published_date"),
                        extra_data={"source": "newsroom"}
                    ):
                        new_items += 1
                break  # Found working newsroom
            except Exception as e:
                logger.debug(f"Could not scrape newsroom {newsroom_url}: {e}")
                continue
        
        # Scrape case studies
        case_study_urls = [
            sources.get("case_studies"),
            f"{sources.get('blog', '').rstrip('/blog')}/case-studies" if sources.get("blog") else None,
            f"{sources.get('blog', '').rstrip('/blog')}/customers" if sources.get("blog") else None,
        ]
        
        for case_url in case_study_urls:
            if not case_url:
                continue
            try:
                items = self._scrape_case_studies(case_url)
                for item in items:
                    if self.save_item(
                        title=item["title"],
                        content=item["content"],
                        source_url=item["url"],
                        published_date=item.get("published_date"),
                        extra_data={"source": "case_study"}
                    ):
                        new_items += 1
                break
            except Exception as e:
                logger.debug(f"Could not scrape case studies {case_url}: {e}")
                continue
        
        return new_items
    
    def _scrape_blog_rss(self, blog_url: str) -> List[Dict]:
        """Scrape blog RSS feed"""
        items = []
        
        # Try multiple RSS feed URLs
        rss_urls = [
            blog_url if blog_url.endswith((".xml", "/feed", "/rss")) else None,
            f"{blog_url.rstrip('/')}/feed",
            f"{blog_url.rstrip('/')}/rss",
            f"{blog_url.rstrip('/')}/rss.xml",
            f"{blog_url.rstrip('/')}/feed.xml",
        ]
        
        for rss_url in rss_urls:
            if not rss_url:
                continue
            
            try:
                feed = feedparser.parse(rss_url)
                
                if feed.bozo:
                    continue
                
                if not feed.entries:
                    continue
                
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
                        
                        # Try to fetch full content
                        if link:
                            try:
                                full_content = self._fetch_article_content(link)
                                if full_content and len(full_content) > len(content):
                                    content = full_content
                            except Exception:
                                pass
                        
                        if not content or len(content) < 100:
                            continue
                        
                        items.append({
                            "title": title,
                            "content": content,
                            "url": link,
                            "published_date": published_date
                        })
                        
                    except Exception as e:
                        logger.debug(f"Error processing blog entry: {e}")
                        continue
                
                if items:
                    break  # Found working RSS feed
                    
            except Exception as e:
                logger.debug(f"Error parsing RSS {rss_url}: {e}")
                continue
        
        return items
    
    def _scrape_newsroom(self, newsroom_url: str) -> List[Dict]:
        """Scrape newsroom/press releases"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(newsroom_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find press release links
            items = []
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True)
                
                if any(keyword in href.lower() for keyword in ["/press/", "/news/", "/release/", "/announcement/"]):
                    if text and len(text) > 20:
                        full_url = href if href.startswith("http") else f"{newsroom_url.rstrip('/')}/{href.lstrip('/')}"
                        
                        # Fetch content
                        content = self._fetch_article_content(full_url)
                        if content and len(content) > 100:
                            items.append({
                                "title": text,
                                "content": content,
                                "url": full_url,
                                "published_date": None
                            })
            
            return items[:10]
            
        except Exception as e:
            logger.debug(f"Error scraping newsroom: {e}")
            return []
    
    def _scrape_case_studies(self, case_url: str) -> List[Dict]:
        """Scrape case studies page"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(case_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find case study links
            items = []
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True)
                
                if any(keyword in href.lower() for keyword in ["/case-study/", "/customer/", "/success-story/"]):
                    if text and len(text) > 20:
                        full_url = href if href.startswith("http") else f"{case_url.rstrip('/')}/{href.lstrip('/')}"
                        
                        # Fetch content
                        content = self._fetch_article_content(full_url)
                        if content and len(content) > 100:
                            items.append({
                                "title": f"Case Study: {text}",
                                "content": content,
                                "url": full_url,
                                "published_date": None
                            })
            
            return items[:10]
            
        except Exception as e:
            logger.debug(f"Error scraping case studies: {e}")
            return []
    
    def _fetch_article_content(self, url: str) -> str:
        """Fetch full article content"""
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
            content_selectors = ["article", ".article-content", ".post-content", "main", ".content"]
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

