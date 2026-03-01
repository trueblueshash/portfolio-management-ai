"""
G2 review scraper using Playwright for JavaScript rendering.
Requires: pip install playwright && playwright install chromium
"""
import logging
import re
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from app.scrapers.base_scraper import BaseScraper
import time
import random

logger = logging.getLogger(__name__)


class G2Scraper(BaseScraper):
    """Scrape G2 reviews using Playwright for JS rendering."""
    
    # Manual mapping for known portfolio companies and competitors
    G2_SLUG_MAP = {
        # Portfolio companies
        "Acceldata": "acceldata",
        "Zluri": "zluri",
        "Scrut Automation": "scrut-automation",
        "Scrut": "scrut-automation",
        "Triomics": "triomics",
        "Emergent.sh": "emergent",
        "Sarvam.ai": "sarvam",
        "Exponent Energy": "exponent-energy",
        "Portkey": "portkey",
        "Pintu": "pintu",
        "Airbound": "airbound",
        "Pixxel": "pixxel",
        "Rattle": "rattle",
        "Thena": "thena",
        "LogicFlo": "logicflo",
        "Coral": "coral",
        "Qure.ai": "qure-ai",
        "Gushworks": "gushworks",
        "Pepper Content": "pepper-content",
        "Aqqrue": "aqqrue",
        "Bridgetown Research": "bridgetown-research",
        "Yellow.ai": "yellow-ai",
        "Darwinbox": "darwinbox",
        
        # Competitors - Data Observability
        "Monte Carlo Data": "monte-carlo",
        "Monte Carlo": "monte-carlo",
        "Atlan": "atlan",
        "Collibra": "collibra",
        "Alation": "alation",
        "Informatica": "informatica",
        "Pantomath": "pantomath",
        "Select Star": "select-star",
        "Datafold": "datafold",
        
        # Competitors - SaaS Management
        "Torii": "torii",
        "Zylo": "zylo",
        "Productiv": "productiv",
        "Josys": "josys",
        "Vertice": "vertice",
        "Cledara": "cledara",
        "Vendr": "vendr",
        "BetterCloud": "bettercloud",
        
        # Competitors - Compliance
        "Vanta": "vanta",
        "Drata": "drata",
        "Secureframe": "secureframe",
        "Tugboat Logic": "tugboat-logic",
        "Laika": "laika",
        "Thoropass": "thoropass",
        "OneTrust": "onetrust",
        
        # Competitors - Healthcare/Genomics
        "Foundation Medicine": "foundation-medicine",
        "Tempus": "tempus",
        "Guardant Health": "guardant-health",
        "NantHealth": "nanthealth",
        "SOPHiA Genetics": "sophia-genetics",
        "Illumina": "illumina",
        
        # Competitors - AI/Development
        "Lovable.dev": "lovable",
        "Cursor": "cursor",
        "Replit": "replit",
        "GitHub Copilot": "github-copilot",
        "v0.dev": "v0",
        "Bolt.new": "bolt-new",
        "Codeium": "codeium",
        "Windsurf": "windsurf",
        "AI4Bharat": "ai4bharat",
        "Bhashini": "bhashini",
        "Krutrim": "krutrim",
        "CoRover.ai": "corover",
        "Gnani.ai": "gnani",
        "Slang Labs": "slang-labs",
        
        # Competitors - EV/Energy
        "ChargePoint": "chargepoint",
        "ABB E-mobility": "abb-e-mobility",
        "Jio-BP": "jio-bp",
        "Ather Energy": "ather-energy",
        "Statiq": "statiq",
        "Kazam": "kazam",
        "Magenta": "magenta",
        
        # Competitors - AI/LLM Ops
        "LangSmith": "langsmith",
        "Helicone": "helicone",
        "Arize AI": "arize-ai",
        "Weights & Biases": "weights-biases",
        "Humanloop": "humanloop",
        "PromptLayer": "promptlayer",
        "Braintrust": "braintrust",
        
        # Competitors - Crypto
        "Tokocrypto": "tokocrypto",
        "Reku": "reku",
        "Indodax": "indodax",
        "Binance": "binance",
        "Coinbase": "coinbase",
        "Kraken": "kraken",
        "OKX": "okx",
        
        # Competitors - Drones/Logistics
        "Zipline": "zipline",
        "Wing": "wing",
        "Amazon Prime Air": "amazon-prime-air",
        "Flytrex": "flytrex",
        "Manna Aero": "manna-aero",
        "Swoop Aero": "swoop-aero",
        "TechEagle": "techeagle",
        
        # Competitors - Satellite/Imaging
        "Planet Labs": "planet-labs",
        "Maxar": "maxar",
        "Satellogic": "satellogic",
        "Spire Global": "spire-global",
        "BlackSky": "blacksky",
        "Capella Space": "capella-space",
        "ICEYE": "iceye",
        
        # Competitors - Sales/Revenue Ops
        "Clari": "clari",
        "Gong": "gong",
        "Salesloft": "salesloft",
        "Outreach": "outreach",
        "Troops.ai": "troops",
        "Sweep": "sweep",
        
        # Competitors - Customer Success
        "Intercom": "intercom",
        "Zendesk": "zendesk",
        "Front": "front",
        "Kustomer": "kustomer",
        "Plain": "plain",
        "HelpScout": "helpscout",
        "Assembled": "assembled",
        
        # Competitors - Automation
        "Zapier": "zapier",
        "Make": "make",
        "Workato": "workato",
        "Tray.io": "tray-io",
        "UiPath": "uipath",
        "Automation Anywhere": "automation-anywhere",
        "Power Automate": "power-automate",
        
        # Competitors - Climate/Carbon
        "Watershed": "watershed",
        "Persefoni": "persefoni",
        "Sweep": "sweep",
        "Greenly": "greenly",
        "Plan A": "plan-a",
        "Normative": "normative",
        "Sphera": "sphera",
        
        # Competitors - Healthcare AI
        "Zebra Medical Vision": "zebra-medical-vision",
        "Aidoc": "aidoc",
        "Viz.ai": "viz-ai",
        "HeartFlow": "heartflow",
        "Imagen Technologies": "imagen-technologies",
        "Lunit": "lunit",
        
        # Competitors - Creator Economy
        "CreatorIQ": "creatoriq",
        "AspireIQ": "aspireiq",
        "GRIN": "grin",
        "Upfluence": "upfluence",
        "Traackr": "traackr",
        "Klear": "klear",
        "LTK": "ltk",
        
        # Competitors - Content
        "Contently": "contently",
        "Skyword": "skyword",
        "Scripted": "scripted",
        "ClearVoice": "clearvoice",
        "WriterAccess": "writeraccess",
        "Jasper.ai": "jasper",
        "Copy.ai": "copy-ai",
        "MarketMuse": "marketmuse",
        
        # Competitors - Treasury/Finance
        "Kyriba": "kyriba",
        "GTreasury": "gtreasury",
        "Trovata": "trovata",
        "Cashforce": "cashforce",
        "HighRadius": "highradius",
        "Tesorio": "tesorio",
        "Ramp": "ramp",
        "Brex": "brex",
        
        # Competitors - Research
        "Bain Accelerate": "bain-accelerate",
        "AlphaSights": "alphasights",
        "GLG": "glg",
        "Third Bridge": "third-bridge",
        "Tegus": "tegus",
        "Stream": "stream",
        "Elicit": "elicit",
        
        # Competitors - Conversational AI
        "Ada": "ada",
        "Boost.ai": "boost-ai",
        "Kore.ai": "kore-ai",
        "LivePerson": "liveperson",
        "Freshworks": "freshworks",
        "Haptik": "haptik",
        
        # Competitors - HRMS
        "Workday": "workday",
        "SAP SuccessFactors": "sap-successfactors",
        "Oracle HCM Cloud": "oracle-hcm-cloud",
        "BambooHR": "bamboohr",
        "Personio": "personio",
        "Zoho People": "zoho-people",
        "Keka": "keka",
        "greytHR": "greythr",
    }
    
    def get_source_type(self) -> str:
        return "g2"
    
    def scrape(self) -> int:
        """Scrape G2 reviews for company and top competitors."""
        count = 0
        
        # Scrape company's own G2 page
        count += self._scrape_company_reviews(self.company.name)
        
        # Scrape top 3 competitors
        for competitor in self.company.competitors[:3]:
            count += self._scrape_company_reviews(competitor)
            time.sleep(random.uniform(3, 6))  # Random delay to avoid detection
        
        return count
    
    def _scrape_company_reviews(self, company_name: str) -> int:
        """Scrape reviews for a specific company."""
        logger.info(f"  🔍 Scraping G2 for: {company_name}")
        
        # Get slug from mapping or generate
        slug = self.G2_SLUG_MAP.get(company_name)
        
        if not slug:
            # Fallback: generate slug
            # Remove common suffixes like "Data", "Inc", "Ltd", ".ai", ".sh"
            clean_name = company_name.replace(" Data", "").replace(" Inc", "").replace(".ai", "").replace(".sh", "").replace(".dev", "")
            slug = clean_name.lower().replace(' ', '-').replace('.', '').replace('&', 'and')
            # Remove special characters
            slug = re.sub(r'[^a-z0-9-]', '', slug)
        
        reviews_url = f"https://www.g2.com/products/{slug}/reviews"
        logger.info(f"    📍 URL: {reviews_url}")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
                
                # Navigate directly to reviews page
                response = page.goto(reviews_url, wait_until="domcontentloaded", timeout=15000)
                
                if response and response.status == 404:
                    logger.warning(f"    ⏭️  404 - Product not found on G2: {reviews_url}")
                    browser.close()
                    return 0
                
                logger.info(f"    ✅ Page loaded successfully")
                time.sleep(3)  # Wait for reviews to render
                
                # Debug: Log page information
                logger.debug(f"    Page title: {page.title()}")
                html = page.content()
                all_divs = page.locator('div').count()
                logger.debug(f"    Total divs on page: {all_divs}")
                
                # Try multiple selectors to find reviews (G2 updates HTML frequently)
                review_selectors = [
                    'div[data-review-id]',  # G2 often uses data attributes
                    '[itemprop="review"]',  # Original schema.org
                    'div.review',
                    'div[class*="Review"]',
                    'div[class*="review"]',
                    'article',  # Plain article tag
                    'article[class*="review"]',
                    'div[class*="Paper"]',
                    'div.paper',
                    'div[class*="Card"]',
                    'div[class*="card"]',
                ]
                
                reviews = []
                for selector in review_selectors:
                    try:
                        found = page.locator(selector).all()
                        if len(found) > 0:
                            logger.info(f"    ✅ Found {len(found)} elements with selector: '{selector}'")
                            reviews = found[:10]  # Limit to 10
                            break
                    except Exception as e:
                        logger.debug(f"    Selector '{selector}' failed: {e}")
                        continue
                
                # If no reviews found, take screenshot and log warning
                if len(reviews) == 0:
                    try:
                        screenshot_path = f"debug_g2_{slug}.png"
                        page.screenshot(path=screenshot_path)
                        logger.warning(f"    ⚠️  No reviews found. Screenshot saved: {screenshot_path}")
                        logger.info(f"    💡 Manually inspect the page to find correct selectors")
                        
                        # Option to save HTML for inspection (uncomment if needed)
                        # with open(f"debug_g2_{slug}.html", "w", encoding="utf-8") as f:
                        #     f.write(html)
                        # logger.info(f"    💾 HTML saved to: debug_g2_{slug}.html")
                    except Exception as e:
                        logger.debug(f"    Could not save screenshot: {e}")
                    
                    browser.close()
                    return 0
                
                logger.info(f"    📊 Processing {len(reviews)} reviews")
                review_count = 0
                
                for review in reviews:
                    try:
                        # Try multiple ways to extract review data
                        # Rating - try multiple selectors
                        rating = "N/A"
                        rating_selectors = [
                            '[itemprop="ratingValue"]',
                            '[data-rating]',
                            '.rating',
                            '[class*="rating"]',
                            '[class*="star"]',
                        ]
                        for rating_sel in rating_selectors:
                            try:
                                rating_elem = review.locator(rating_sel).first
                                if rating_elem.count() > 0:
                                    rating = rating_elem.get_attribute("content") or rating_elem.get_attribute("data-rating") or rating_elem.inner_text()
                                    if rating:
                                        break
                            except:
                                continue
                        
                        # Title - try multiple selectors
                        review_title = "Review"
                        title_selectors = [
                            '[itemprop="name"]',
                            'h3',
                            'h4',
                            '[class*="title"]',
                            '[class*="heading"]',
                        ]
                        for title_sel in title_selectors:
                            try:
                                title_elem = review.locator(title_sel).first
                                if title_elem.count() > 0:
                                    review_title = title_elem.inner_text().strip()
                                    if review_title:
                                        break
                            except:
                                continue
                        
                        # Review text - try multiple selectors
                        review_text = ""
                        text_selectors = [
                            '[itemprop="reviewBody"]',
                            '[class*="review"]',
                            '[class*="text"]',
                            '[class*="content"]',
                            'p',
                        ]
                        for text_sel in text_selectors:
                            try:
                                text_elem = review.locator(text_sel).first
                                if text_elem.count() > 0:
                                    review_text = text_elem.inner_text().strip()
                                    if review_text and len(review_text) > 20:
                                        break
                            except:
                                continue
                        
                        # Date - try multiple selectors
                        date_str = None
                        date_selectors = [
                            '[itemprop="datePublished"]',
                            '[class*="date"]',
                            '[class*="time"]',
                            'time',
                        ]
                        for date_sel in date_selectors:
                            try:
                                date_elem = review.locator(date_sel).first
                                if date_elem.count() > 0:
                                    date_str = date_elem.get_attribute("content") or date_elem.get_attribute("datetime") or date_elem.inner_text()
                                    if date_str:
                                        break
                            except:
                                continue
                        
                        # Parse date
                        review_date = None
                        if date_str:
                            try:
                                review_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            except:
                                pass
                        
                        # Get review URL
                        review_url = f"{reviews_url}#{review_title.replace(' ', '-').lower()}"
                        
                        # Format content
                        content = f"Rating: {rating}/5\n\n{review_text}"
                        title_formatted = f"G2 Review ({rating}⭐): {review_title} - {company_name}"
                        
                        # Save review (with AI relevance check)
                        saved = self.save_item(
                            title=title_formatted,
                            content=content,
                            source_url=review_url,
                            published_date=review_date,
                            extra_data={
                                "source": "g2",
                                "rating": rating,
                                "company_name": company_name
                            }
                        )
                        
                        if saved:
                            review_count += 1
                        
                    except Exception as e:
                        logger.debug(f"    Error extracting review: {e}")
                        continue
                
                browser.close()
                logger.info(f"    ✅ {company_name}: {review_count} relevant reviews")
                return review_count
                
        except PlaywrightTimeout:
            logger.warning(f"    ⏭️  Timeout loading G2 for {company_name}")
            return 0
        except Exception as e:
            logger.error(f"    ❌ Error scraping G2 for {company_name}: {e}")
            return 0
