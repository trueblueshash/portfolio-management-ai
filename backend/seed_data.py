"""
Seed script to populate database with 23 portfolio companies.
Run with: python seed_data.py
"""
import sys
from app.db.session import SessionLocal
from app.models.company import Company

COMPANIES_DATA = [
    {
        "name": "Acceldata",
        "market_tags": ["data observability", "data catalog", "data governance", "data quality", "data management", "agentic data management", "DataOps", "metadata management"],
        "competitors": ["Monte Carlo Data", "Atlan", "Collibra", "Alation", "Informatica", "Pantomath", "Select Star", "Datafold"],
        "sources": {
            "blog": "https://www.acceldata.io/blog",
            "twitter": "@acceldataio",
            "linkedin": "acceldata"
        }
    },
    {
        "name": "Zluri",
        "market_tags": ["SaaS management", "IT asset management", "shadow IT discovery", "license optimization", "spend management", "access governance", "SaaS operations"],
        "competitors": ["Torii", "Zylo", "Productiv", "Josys", "Vertice", "Cledara", "Vendr", "BetterCloud"],
        "sources": {
            "blog": "https://www.zluri.com/blog",
            "twitter": "@zlurihq",
            "linkedin": "zluri"
        }
    },
    {
        "name": "Scrut Automation",
        "market_tags": ["GRC automation", "compliance automation", "SOC 2", "ISO 27001", "HIPAA compliance", "security compliance", "continuous compliance", "risk management"],
        "competitors": ["Vanta", "Drata", "Secureframe", "Tugboat Logic", "Laika", "Thoropass", "OneTrust"],
        "sources": {
            "blog": "https://www.scrut.io/blog",
            "linkedin": "scrut-automation"
        }
    },
    {
        "name": "Triomics",
        "market_tags": ["precision oncology", "genomics data platform", "cancer diagnostics", "liquid biopsy", "NGS analysis", "clinical genomics", "molecular profiling"],
        "competitors": ["Foundation Medicine", "Tempus", "Guardant Health", "NantHealth", "SOPHiA Genetics", "Illumina"],
        "sources": {}
    },
    {
        "name": "Emergent.sh",
        "market_tags": ["AI-powered development", "agentic coding", "software engineering automation", "code generation", "full-stack development", "AI IDE", "autonomous development"],
        "competitors": ["Lovable.dev", "Cursor", "Replit", "GitHub Copilot", "v0.dev", "Bolt.new", "Codeium", "Windsurf"],
        "sources": {}
    },
    {
        "name": "Sarvam.ai",
        "market_tags": ["Indic language AI", "LLM for Indian languages", "speech-to-text", "text-to-speech", "voice AI", "multilingual NLP", "generative AI", "foundation models"],
        "competitors": ["AI4Bharat", "Bhashini", "Krutrim", "CoRover.ai", "Gnani.ai", "Slang Labs"],
        "sources": {}
    },
    {
        "name": "Exponent Energy",
        "market_tags": ["EV fast charging", "battery technology", "energy storage", "e-mobility infrastructure", "commercial EV charging", "energy-as-a-service", "rapid charging"],
        "competitors": ["ChargePoint", "ABB E-mobility", "Jio-BP", "Ather Energy", "Statiq", "Kazam", "Magenta"],
        "sources": {}
    },
    {
        "name": "Portkey",
        "market_tags": ["AI gateway", "LLM ops", "prompt management", "AI observability", "model routing", "AI infrastructure", "multi-model orchestration", "prompt engineering"],
        "competitors": ["LangSmith", "Helicone", "Arize AI", "Weights & Biases", "Humanloop", "PromptLayer", "Braintrust"],
        "sources": {}
    },
    {
        "name": "Pintu",
        "market_tags": ["cryptocurrency exchange", "crypto trading platform", "digital asset platform", "crypto wallet", "Web3 finance", "retail crypto trading"],
        "competitors": ["Tokocrypto", "Reku", "Indodax", "Binance", "Coinbase", "Kraken", "OKX"],
        "sources": {}
    },
    {
        "name": "Airbound",
        "market_tags": ["drone delivery", "logistics automation", "last-mile delivery", "aerial logistics", "UAV technology", "supply chain innovation", "autonomous delivery"],
        "competitors": ["Zipline", "Wing", "Amazon Prime Air", "Flytrex", "Manna Aero", "Swoop Aero", "TechEagle"],
        "sources": {}
    },
    {
        "name": "Pixxel",
        "market_tags": ["satellite imaging", "hyperspectral imaging", "earth observation", "remote sensing", "geospatial analytics", "climate monitoring", "agricultural tech", "space technology"],
        "competitors": ["Planet Labs", "Maxar", "Satellogic", "Spire Global", "BlackSky", "Capella Space", "ICEYE"],
        "sources": {}
    },
    {
        "name": "Rattle",
        "market_tags": ["Salesforce automation", "revenue operations", "sales productivity", "CRM workflow automation", "deal desk automation", "quote-to-cash", "sales enablement"],
        "competitors": ["Clari", "Gong", "Salesloft", "Outreach", "Troops.ai", "Sweep"],
        "sources": {}
    },
    {
        "name": "Thena",
        "market_tags": ["B2B customer communication", "customer success platform", "Slack-based support", "community engagement", "customer relationship management", "B2B support automation"],
        "competitors": ["Intercom", "Zendesk", "Front", "Kustomer", "Plain", "HelpScout", "Assembled"],
        "sources": {}
    },
    {
        "name": "LogicFlo",
        "market_tags": ["process automation", "workflow automation", "business process management", "no-code automation", "enterprise automation", "operational efficiency"],
        "competitors": ["Zapier", "Make", "Workato", "Tray.io", "UiPath", "Automation Anywhere", "Power Automate"],
        "sources": {}
    },
    {
        "name": "Coral",
        "market_tags": ["carbon accounting", "climate tech", "sustainability reporting", "ESG compliance", "emissions tracking", "carbon management", "climate data platform"],
        "competitors": ["Watershed", "Persefoni", "Sweep", "Greenly", "Plan A", "Normative", "Sphera"],
        "sources": {}
    },
    {
        "name": "Qure.ai",
        "market_tags": ["medical imaging AI", "radiology AI", "diagnostic automation", "healthcare AI", "deep learning in healthcare", "chest X-ray AI", "CT scan analysis", "stroke detection"],
        "competitors": ["Zebra Medical Vision", "Aidoc", "Viz.ai", "HeartFlow", "Imagen Technologies", "Lunit"],
        "sources": {}
    },
    {
        "name": "Gushworks",
        "market_tags": ["creator economy", "influencer marketing", "creator management platform", "brand partnerships", "influencer analytics", "social media marketing", "creator monetization"],
        "competitors": ["CreatorIQ", "AspireIQ", "GRIN", "Upfluence", "Traackr", "Klear", "LTK"],
        "sources": {}
    },
    {
        "name": "Pepper Content",
        "market_tags": ["content marketing platform", "content creation", "AI content generation", "content operations", "SEO content", "content workflow", "freelance marketplace", "content automation"],
        "competitors": ["Contently", "Skyword", "Scripted", "ClearVoice", "WriterAccess", "Jasper.ai", "Copy.ai", "MarketMuse"],
        "sources": {}
    },
    {
        "name": "Aqqrue",
        "market_tags": ["treasury management", "cash management", "corporate banking", "financial automation", "AP/AR automation", "working capital optimization", "embedded finance"],
        "competitors": ["Kyriba", "GTreasury", "Trovata", "Cashforce", "HighRadius", "Tesorio", "Ramp", "Brex"],
        "sources": {}
    },
    {
        "name": "Bridgetown Research",
        "market_tags": ["AI-powered research", "autonomous research agents", "business intelligence automation", "commercial due diligence", "market research automation", "expert network automation", "decision intelligence"],
        "competitors": ["Bain Accelerate", "AlphaSights", "GLG", "Third Bridge", "Tegus", "Stream", "Elicit"],
        "sources": {
            "blog": "https://www.bridgetownresearch.com",
            "linkedin": "bridgetownresearch"
        }
    },
    {
        "name": "Yellow.ai",
        "market_tags": ["conversational AI", "chatbot platform", "enterprise AI agents", "voice AI", "customer service automation", "NLP platform", "omnichannel support", "generative AI chatbots"],
        "competitors": ["Intercom", "Zendesk", "Ada", "Boost.ai", "Kore.ai", "LivePerson", "Freshworks", "Haptik"],
        "sources": {}
    },
    {
        "name": "Darwinbox",
        "market_tags": ["HRMS", "human capital management", "HR tech", "talent management", "payroll software", "employee engagement", "performance management", "workforce analytics", "HR automation"],
        "competitors": ["Workday", "SAP SuccessFactors", "Oracle HCM Cloud", "BambooHR", "Personio", "Zoho People", "Keka", "greytHR"],
        "sources": {}
    }
]


def seed_companies():
    """Seed the database with companies"""
    db = SessionLocal()
    try:
        for company_data in COMPANIES_DATA:
            # Check if company already exists
            existing = db.query(Company).filter(Company.name == company_data["name"]).first()
            if existing:
                print(f"Company '{company_data['name']}' already exists, skipping...")
                continue
            
            company = Company(**company_data)
            db.add(company)
            print(f"Added company: {company_data['name']}")
        
        db.commit()
        print(f"\nSuccessfully seeded {len(COMPANIES_DATA)} companies!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding companies: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_companies()

