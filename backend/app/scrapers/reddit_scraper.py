"""
Reddit scraper for monitoring discussions about company and competitors.
"""
import logging
import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict
from app.scrapers.base_scraper import BaseScraper
from app.models.company import Company
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RedditScraper(BaseScraper):
    """Scrape Reddit for company and competitor mentions"""
    
    # Map market tags to relevant subreddits
    SUBREDDIT_MAP = {
        "saas": ["r/SaaS", "r/startups"],
        "ai": ["r/MachineLearning", "r/artificial", "r/LocalLLaMA"],
        "data": ["r/dataengineering", "r/datascience"],
        "devops": ["r/devops", "r/sysadmin"],
        "security": ["r/cybersecurity", "r/netsec"],
        "fintech": ["r/fintech", "r/investing"],
        "healthcare": ["r/healthcare", "r/medicine"],
    }
    
    def get_source_type(self) -> str:
        return "reddit"
    
    def scrape(self) -> int:
        """Scrape Reddit for company and competitor mentions"""
        new_items = 0
        
        # Get relevant subreddits
        subreddits = self._get_relevant_subreddits()
        
        # Search queries: company name and competitors
        search_queries = [self.company.name]
        search_queries.extend(self.company.competitors[:3])  # Limit to 3 competitors
        
        for query in search_queries:
            for subreddit in subreddits:
                try:
                    items = self._search_reddit(query, subreddit)
                    for item in items:
                        if self.save_item(
                            title=item["title"],
                            content=item["content"],
                            source_url=item["url"],
                            published_date=item.get("published_date"),
                            extra_data={
                                "subreddit": subreddit,
                                "search_query": query,
                                "score": item.get("score", 0),
                                "comments": item.get("num_comments", 0)
                            }
                        ):
                            new_items += 1
                    
                    # Rate limiting
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ Error scraping Reddit '{subreddit}' for '{query}': {e}")
                    continue
        
        return new_items
    
    def _get_relevant_subreddits(self) -> List[str]:
        """Get relevant subreddits based on market tags"""
        subreddits = set()
        
        # Add default tech subreddits
        subreddits.add("r/technology")
        subreddits.add("r/startups")
        
        # Map market tags to subreddits
        for tag in self.company.market_tags:
            tag_lower = tag.lower()
            for key, subs in self.SUBREDDIT_MAP.items():
                if key in tag_lower:
                    subreddits.update(subs)
        
        return list(subreddits)[:5]  # Limit to 5 subreddits
    
    def _search_reddit(self, query: str, subreddit: str = None) -> List[Dict]:
        """Search Reddit using JSON API (no auth needed)"""
        try:
            # Reddit search URL
            if subreddit:
                url = f"https://www.reddit.com/{subreddit}/search.json"
            else:
                url = "https://www.reddit.com/search.json"
            
            params = {
                "q": query,
                "limit": 10,
                "sort": "new",
                "t": "month"  # Last month
            }
            
            headers = {
                "User-Agent": "PortfolioIntelligence/1.0 (by /u/portfolio_intel)"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if "data" not in data or "children" not in data["data"]:
                return []
            
            items = []
            cutoff_date = datetime.now() - timedelta(days=30)
            
            for child in data["data"]["children"]:
                post = child.get("data", {})
                
                # Parse published date
                published_timestamp = post.get("created_utc", 0)
                if published_timestamp:
                    published_date = datetime.fromtimestamp(published_timestamp)
                    if published_date < cutoff_date:
                        continue
                else:
                    published_date = None
                
                # Build content
                title = post.get("title", "")
                selftext = post.get("selftext", "")
                url = f"https://www.reddit.com{post.get('permalink', '')}"
                
                # Combine title and content
                content = f"{title}\n\n{selftext}".strip()
                
                if not content or len(content) < 100:
                    continue
                
                items.append({
                    "title": title,
                    "content": content,
                    "url": url,
                    "published_date": published_date,
                    "score": post.get("score", 0),
                    "num_comments": post.get("num_comments", 0)
                })
            
            return items
            
        except Exception as e:
            logger.error(f"Error searching Reddit: {e}")
            return []

