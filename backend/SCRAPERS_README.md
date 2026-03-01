# Comprehensive Intelligence Gathering System

## Overview

This system automatically collects strategic intelligence for portfolio companies across multiple sources:
- Company's own content (blogs, newsrooms, case studies)
- Google News monitoring
- Competitor tracking
- Reddit discussions
- Review sites (G2, etc.)

## Architecture

### Base Scraper (`app/scrapers/base_scraper.py`)
- Abstract base class for all scrapers
- Handles deduplication (checks `source_url`)
- AI relevance filtering before saving
- Date filtering (last 60 days)
- Minimum content length check (100 chars)
- Database commit handling

### AI Relevance Filter (`app/services/relevance_filter.py`)
- Uses free Google Gemini Flash model
- Determines if content is relevant to board members
- Returns JSON with:
  - `is_relevant`: boolean
  - `relevance_score`: 0.0-1.0
  - `reason`: why it matters (or doesn't)
  - `category`: product/gtm/traction/market_position/corporate/regulatory
  - `summary`: 2-3 sentence summary

### Scrapers

1. **CompanyContentScraper** (`app/scrapers/company_content.py`)
   - Scrapes company blog RSS feeds
   - Newsroom/press releases
   - Case studies pages
   - Tries multiple RSS URL patterns

2. **NewsScraper** (`app/scrapers/news_scraper.py`)
   - Google News RSS feeds
   - Searches for: company name, competitors, market tags
   - Fetches full article content when possible
   - Filters to last 30 days

3. **CompetitorMonitor** (`app/scrapers/competitor_monitor.py`)
   - Monitors competitor blogs (RSS)
   - Competitor newsrooms
   - Tries multiple URL patterns
   - Limits to 5 competitors per company

4. **RedditScraper** (`app/scrapers/reddit_scraper.py`)
   - Uses Reddit JSON API (no auth needed)
   - Maps market tags to relevant subreddits
   - Searches for company and competitors
   - Filters to last 30 days

5. **ReviewScraper** (`app/scrapers/review_scraper.py`)
   - Basic G2 scraping (limited - requires JS for full functionality)
   - Placeholder for future Selenium implementation

## Usage

### Run for All Companies
```bash
cd backend
python run_comprehensive_scrapers.py
```

### Run for Single Company
```bash
python run_comprehensive_scrapers.py Acceldata
```

## Output

The script shows:
- Progress for each company
- Items found per scraper type
- Summary per company
- Grand total across all companies

Example output:
```
🏢 Processing: Acceldata
📝 Scraping company content...
   ✅ Found 3 new items
📰 Scraping Google News...
   ✅ Found 5 new items
🔍 Monitoring competitors...
   ✅ Found 2 new items
💬 Scraping Reddit discussions...
   ✅ Found 1 new items

📊 Summary for Acceldata:
   Company Content: 3 items
   Google News: 5 items
   Competitors: 2 items
   Reddit: 1 items
   TOTAL: 11 new items
```

## Data Flow

1. Scraper fetches content from source
2. For each item:
   - Check if `source_url` already exists (skip if duplicate)
   - Check content length (skip if < 100 chars)
   - Check date (skip if > 60 days old)
   - Call AI relevance filter
   - If relevant: Save to database with AI summary and category
   - If not relevant: Log and skip
3. Commit all items to database
4. Return count of new items

## Error Handling

- Individual scraper failures don't stop the process
- AI failures fall back to saving with default values (manual review needed)
- Rate limiting between requests (2-3 second delays)
- Graceful handling of missing RSS feeds, invalid URLs, etc.

## Rate Limiting

- 2 seconds between Google News requests
- 2 seconds between Reddit requests
- 3 seconds between competitor requests
- Prevents overwhelming target sites

## Limitations

1. **JS-Rendered Sites**: Some sites (G2, many modern blogs) require JavaScript rendering. Consider Selenium for full functionality.

2. **RSS Feed Discovery**: The system tries common RSS URL patterns, but some sites may need manual configuration.

3. **Content Extraction**: HTML scraping may not always get full content. RSS feeds are more reliable.

4. **Reddit API**: Uses public JSON API which has rate limits. For production, consider Reddit API authentication.

## Future Enhancements

- Selenium integration for JS-rendered sites
- Twitter/X API integration
- LinkedIn monitoring (requires API)
- Hacker News scraping
- Product Hunt monitoring
- Job posting monitoring (LinkedIn, Indeed)
- GitHub activity tracking (for dev tools)
- PR Newswire API integration
- TechCrunch/VentureBeat RSS feeds

## Configuration

All scrapers use the company's `sources` JSON field from the database:
```json
{
  "blog": "https://company.com/blog",
  "newsroom": "https://company.com/newsroom",
  "case_studies": "https://company.com/customers"
}
```

Market tags and competitors are used for:
- Relevance scoring
- Google News searches
- Reddit subreddit mapping
- Competitor monitoring

