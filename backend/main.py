import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from .database import engine, Base, get_db
from .models import Company as CompanyModel
from .schemas import CompanyEnrichRequest, CompanyResponse, CompanyDBResponse
from .scraper import scrape_company_website, normalize_url
from .ai_service import generate_business_insights

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="Company Enrichment API",
    description="AI-powered Company Enrichment Platform backend",
    version="1.0.0"
)

# Enable CORS for React frontend (Vite defaults to port 5173, and allow production origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development and deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event to create tables if they don't exist
@app.on_event("startup")
def startup_db_client():
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")

@app.post("/enrich", response_model=CompanyResponse, status_code=status.HTTP_200_OK)
async def enrich_company(request: CompanyEnrichRequest, db: Session = Depends(get_db)):
    """
    Enriches a company by scraping its website, extracting contact information
    via regex, and generating business insights using AI.
    Implements duplicate URL detection / caching.
    """
    normalized_url = normalize_url(request.url)
    if not normalized_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Provided URL is invalid or empty."
        )

    # 1. Duplicate URL / Cache Detection
    existing_company = db.query(CompanyModel).filter(CompanyModel.website_url == normalized_url).first()
    if existing_company:
        logger.info(f"Cache hit for URL: {normalized_url}. Returning stored insights.")
        if request.website_name and existing_company.website_name != request.website_name:
            existing_company.website_name = request.website_name
            db.commit()
            db.refresh(existing_company)
        return existing_company

    # 2. Scrape Company Website (Priority 1: Sitemap, Priority 2: Crawler, Priority 3: Fallback paths)
    logger.info(f"Cache miss. Scraping URL: {normalized_url}")
    try:
        scraped_data = await scrape_company_website(normalized_url)
    except Exception as e:
        logger.error(f"Failed to scrape website {normalized_url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to access or parse company website: {str(e)}"
        )

    # 3. Generate Business Insights via LLM (Gemini/OpenAI) with Heuristic Fallback
    logger.info(f"Generating AI insights for: {scraped_data['domain']}")
    try:
        ai_insights = await generate_business_insights(scraped_data["domain"], scraped_data["scraped_text"])
    except Exception as e:
        logger.error(f"Failed to generate business insights: {e}")
        # Default fallback values to prevent system crash
        ai_insights = {
            "website_name": scraped_data["domain"].split(".")[0].capitalize(),
            "company_name": "",
            "core_service": "Service details could not be extracted.",
            "target_customer": "Target audience details could not be extracted.",
            "probable_pain_point": "Company pain points could not be inferred.",
            "outreach_opener": "Hi, I noticed your website and would love to connect."
        }

    # 4. Save to Database (Merge Regex Contacts + AI Insights)
    # This structure guarantees the LLM NEVER invents contact information!
    new_company = CompanyModel(
        website_url=normalized_url,
        website_name=request.website_name or ai_insights.get("website_name") or scraped_data["domain"],
        company_name=ai_insights.get("company_name") or request.website_name or "",
        address=scraped_data["address"],
        mobile_number=scraped_data["phones"],
        mail=scraped_data["emails"],
        core_service=ai_insights.get("core_service") or "",
        target_customer=ai_insights.get("target_customer") or "",
        probable_pain_point=ai_insights.get("probable_pain_point") or "",
        outreach_opener=ai_insights.get("outreach_opener") or "",
    )

    try:
        db.add(new_company)
        db.commit()
        db.refresh(new_company)
        logger.info(f"Successfully enriched and saved company: {new_company.website_url}")
        return new_company
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save enriched company to database: {e}")
        # If DB save fails for some reason (e.g. concurrent inserts), return the object directly without DB save
        return new_company

@app.get("/results", response_model=List[CompanyDBResponse])
def get_all_results(db: Session = Depends(get_db)):
    """
    Returns all enriched companies stored in the database, ordered by newest first.
    """
    try:
        companies = db.query(CompanyModel).order_by(CompanyModel.created_at.desc()).all()
        return companies
    except Exception as e:
        logger.error(f"Failed to retrieve results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving enriched companies from database."
        )
