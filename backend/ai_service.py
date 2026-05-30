import os
import json
import logging
from typing import Dict, Any
import google.generativeai as genai
from openai import OpenAI

logger = logging.getLogger(__name__)

# Initialize clients if keys exist
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
You are an expert business analyst. Analyze the provided website scraped text and extract or infer company details.
Strictly adhere to these rules:
1. ONLY use information found in the text.
2. DO NOT invent or assume any values.
3. For 'company_name', extract it only if it is explicitly and clearly stated in the text. Do not guess it. If it is not clearly stated, return an empty string "".
4. Generate business insights for 'core_service', 'target_customer', 'probable_pain_point', and 'outreach_opener' based on page evidence.
5. Your response must be a single, valid JSON object matching the requested schema exactly.

Expected JSON output format:
{
  "website_name": "Extracted site/brand name",
  "company_name": "Explicitly found company name, or empty string",
  "core_service": "Concise summary of their core services/products",
  "target_customer": "Inferred target audience or demographic",
  "probable_pain_point": "Pain points their customers face, solved by this company",
  "outreach_opener": "A personalized 1-2 sentence email opener to hook this company"
}
"""

def heuristic_enrichment(domain: str, text: str) -> Dict[str, Any]:
    """Fallback business heuristics in case LLM API keys are missing or API calls fail."""
    domain_name = domain.replace("www.", "").split(".")[0].capitalize()
    
    # Parse some basic info from text
    core_service = "Company enrichment and intelligence services."
    target_customer = "B2B sales teams, marketers, and growth engineers."
    pain_point = "Manual lead profiling, lack of contact details, low outreach response rates."
    opener = f"Hi team, I came across {domain_name} and was impressed by your digital footprint. I'd love to discuss how we can help you scale."
    
    if text:
        # Simple extraction heuristics based on keyword counts
        text_lower = text.lower()
        if "software" in text_lower or "app" in text_lower or "platform" in text_lower:
            core_service = "Software engineering and digital product development."
            target_customer = "Tech startups, enterprise corporations, and digital agencies."
            pain_point = "Scaling engineering resources, technical debt, and UI/UX design challenges."
        elif "marketing" in text_lower or "seo" in text_lower or "ads" in text_lower:
            core_service = "Digital marketing, brand strategy, and growth marketing services."
            target_customer = "E-commerce brands, local businesses, and B2C platforms."
            pain_point = "High customer acquisition costs, low website conversion rates, and SEO visibility."
        elif "consulting" in text_lower or "advisor" in text_lower or "strategy" in text_lower:
            core_service = "Strategic business consulting and advisory services."
            target_customer = "Executive leaders, SMB owners, and legacy enterprises."
            pain_point = "Operational inefficiencies, corporate restructure, and strategic growth planning."
            
    return {
        "website_name": domain_name,
        "company_name": domain_name,
        "core_service": core_service,
        "target_customer": target_customer,
        "probable_pain_point": pain_point,
        "outreach_opener": opener
    }

async def generate_business_insights(domain: str, scraped_text: str) -> Dict[str, Any]:
    """Generates business insights using Gemini API, OpenAI API, or heuristics fallback."""
    if not scraped_text or len(scraped_text.strip()) < 50:
        return heuristic_enrichment(domain, scraped_text)

    # 1. Try Gemini API
    if GEMINI_API_KEY:
        try:
            # We use gemini-1.5-flash as default, or fallback to gemini-2.5-flash
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_PROMPT
            )
            response = model.generate_content(
                f"Website domain: {domain}\n\nScraped Text:\n{scraped_text}",
                generation_config={"response_mime_type": "application/json"}
            )
            data = json.loads(response.text)
            # Ensure correct format keys are present
            required_keys = ["website_name", "company_name", "core_service", "target_customer", "probable_pain_point", "outreach_opener"]
            if all(k in data for k in required_keys):
                return data
        except Exception as e:
            logger.error(f"Gemini API generation failed: {e}")

    # 2. Try OpenAI API
    if OPENAI_API_KEY:
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Website domain: {domain}\n\nScraped Text:\n{scraped_text}"}
                ],
                temperature=0.2
            )
            data = json.loads(response.choices[0].message.content)
            required_keys = ["website_name", "company_name", "core_service", "target_customer", "probable_pain_point", "outreach_opener"]
            if all(k in data for k in required_keys):
                return data
        except Exception as e:
            logger.error(f"OpenAI API generation failed: {e}")

    # 3. Heuristic Fallback
    logger.info("Using heuristic analysis due to missing keys or API failures.")
    return heuristic_enrichment(domain, scraped_text)
