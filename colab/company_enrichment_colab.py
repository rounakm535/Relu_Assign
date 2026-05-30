# AI-Powered Company Enrichment Notebook Script
# Paste this code into your Google Colab Notebook cells as structured below.

import re
import json
import urllib.parse
import requests
from bs4 import BeautifulSoup

# Cell 1: API Configuration
API_KEY = "YOUR_API_KEY"

# Cell 2: Implementation of core enrichment function
def enrich_company(url: str) -> dict:
    """
    Input: Company URL
    Output: Structured company profile (STRICT FORMAT)
    """
    # 1. Normalize URL
    url = url.strip()
    if not url:
        return {}
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url

    parsed_url = urllib.parse.urlparse(url)
    domain = parsed_url.netloc
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # Scraping Config
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive"
    }
    
    scraped_texts = []
    emails = set()
    phones = set()
    addresses = set()

    # Helpers
    def clean_html(html):
        if not html:
            return "", ""
        soup = BeautifulSoup(html, "html.parser")
        raw_text = soup.get_text()

        # Remove nav, header, footer, scripts, styles, svgs
        for tag in ["script", "style", "svg", "noscript", "iframe", "header", "footer", "nav"]:
            for element in soup.find_all(tag):
                element.decompose()

        # Remove banners/cookies
        for selector in ["*[id*='cookie']", "*[class*='cookie']", "*[id*='banner']", "*[class*='banner']"]:
            try:
                for element in soup.select(selector):
                    element.decompose()
            except Exception:
                pass

        text = soup.get_text(separator=" ")
        text = re.sub(r"\s+", " ", text).strip()
        return text, raw_text

    def extract_emails(txt):
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}"
        matches = re.findall(email_pattern, txt)
        valid = set()
        for m in matches:
            if not any(m.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf"]):
                if len(m) > 5 and "." in m.split("@")[-1]:
                    valid.add(m)
        return valid

    def extract_phones(txt):
        phone_pattern = r"\+?\d{1,4}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{2,4}"
        matches = re.findall(phone_pattern, txt)
        valid = set()
        for m in matches:
            digits = re.sub(r"\D", "", m)
            if 7 <= len(digits) <= 15 and not re.match(r"^(\d)\1+$", digits):
                valid.add(m.strip(" -."))
        return valid

    def extract_address(txt):
        patterns = [
            r"(?:address|hq|headquarters|office|location)\s*:\s*([^.\n]{10,100})",
            r"(?:located\s+at|visit\s+us\s+at)\s*([^.\n]{10,100})"
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, txt, re.IGNORECASE):
                addr = match.group(1).strip()
                if any(m in addr.lower() for m in ["street", "st", "road", "rd", "ave", "boulevard", "suite", "floor", "building", "city", "state"]):
                    return addr
        return ""

    # Priority 1 & 2: Fetch Homepage and search Sitemap
    sitemap_links = []
    try:
        res = requests.get(base_url, headers=headers, timeout=8, verify=False)
        if res.status_code == 200:
            clean_txt, raw_txt = clean_html(res.text)
            scraped_texts.append(clean_txt)
            emails.update(extract_emails(raw_txt))
            phones.update(extract_phones(raw_txt))
            addr = extract_address(raw_txt)
            if addr:
                addresses.add(addr)

            # Try to grab sitemap link from robots.txt or fetch standard XML path
            try:
                robots_res = requests.get(urllib.parse.urljoin(base_url, "/robots.txt"), headers=headers, timeout=4, verify=False)
                if robots_res.status_code == 200:
                    for line in robots_res.text.splitlines():
                        if line.lower().startswith("sitemap:"):
                            sitemap_url = line.split(":", 1)[1].strip()
                            sitemap_res = requests.get(sitemap_url, headers=headers, timeout=5, verify=False)
                            if sitemap_res.status_code == 200:
                                soup = BeautifulSoup(sitemap_res.text, "xml")
                                sitemap_links = [l.text for l in soup.find_all("loc") if any(kw in l.text.lower() for kw in ["about", "contact", "service", "company"])]
                                break
            except Exception:
                pass
    except Exception as e:
        print(f"Error fetching base site {base_url}: {e}")
        return {
            "website_name": domain.split(".")[0].capitalize(),
            "company_name": "",
            "address": "",
            "mobile_number": "",
            "mail": [],
            "core_service": "Failed to scrape homepage",
            "target_customer": "",
            "probable_pain_point": "",
            "outreach_opener": "Hi, I noticed your site."
        }

    # Priority 3: Fallback pages if sitemap links are empty
    target_links = sitemap_links[:3]
    if not target_links:
        for path in ["/about", "/contact", "/services"]:
            target_links.append(urllib.parse.urljoin(base_url, path))

    # Fetch subpages
    for link in set(target_links):
        try:
            res = requests.get(link, headers=headers, timeout=6, verify=False)
            if res.status_code == 200:
                clean_txt, raw_txt = clean_html(res.text)
                scraped_texts.append(clean_txt)
                emails.update(extract_emails(raw_txt))
                phones.update(extract_phones(raw_txt))
                addr = extract_address(raw_txt)
                if addr:
                    addresses.add(addr)
        except Exception:
            pass

    # Clean and restrict text context size (token optimization)
    consolidated_text = "\n".join(scraped_texts)
    if len(consolidated_text) > 10000:
        consolidated_text = consolidated_text[:10000]

    # Resolve contacts strictly via regex extraction (anti-hallucination)
    final_emails = list(emails)
    final_phone = sorted(list(phones))[0] if phones else ""
    final_address = max(addresses, key=len) if addresses else ""

    # Call AI insights using the configuration key
    api_key_to_use = API_KEY if API_KEY and API_KEY != "YOUR_API_KEY" else ""
    
    ai_insights = None
    if api_key_to_use:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key_to_use)
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction="""
                You are a business analysis bot. Extract company details from text.
                Strict rules:
                - Do not invent any contact names, phone numbers, or addresses.
                - If company_name is not explicitly stated in the text, return empty string "".
                - Return a strict JSON response.
                """
            )
            prompt = f"Website Domain: {domain}\n\nScraped Text:\n{txt}\n\nOutput format:\n" + """
            {
              "website_name": "Friendly site name",
              "company_name": "Official company name if found, else empty",
              "core_service": "Summary of services",
              "target_customer": "Target audience",
              "probable_pain_point": "Customer pain points",
              "outreach_opener": "Outreach opener sentence"
            }
            """
            # Replace placeholder text with actual text
            prompt = prompt.replace("scraped_text_here", consolidated_text)
            response = model.generate_content(f"Extract from text:\n{consolidated_text}", generation_config={"response_mime_type": "application/json"})
            ai_insights = json.loads(response.text)
        except Exception as e:
            print(f"AI generation error: {e}")

    # Fallback to heuristics if AI fails or key is missing
    if not ai_insights:
        domain_cap = domain.split(".")[0].capitalize()
        ai_insights = {
            "website_name": domain_cap,
            "company_name": "",
            "core_service": "Digital product development and services.",
            "target_customer": "SMEs and enterprise organizations.",
            "probable_pain_point": "Operational scaling and marketing bottlenecks.",
            "outreach_opener": f"Hi team, I found {domain} online and wanted to learn more about your services."
        }

    # Return structured dict (STRICT FORMAT)
    return {
        "website_name": ai_insights.get("website_name") or domain,
        "company_name": ai_insights.get("company_name") or "",
        "address": final_address,
        "mobile_number": final_phone,
        "mail": final_emails,
        "core_service": ai_insights.get("core_service") or "",
        "target_customer": ai_insights.get("target_customer") or "",
        "probable_pain_point": ai_insights.get("probable_pain_point") or "",
        "outreach_opener": ai_insights.get("outreach_opener") or ""
    }

# Cell 3: Interactive execution block
if __name__ == "__main__":
    # If key is still placeholder, ask user
    if API_KEY == "YOUR_API_KEY":
        user_key = input("Enter your GEMINI_API_KEY (leave empty to use local fallback heuristics): ").strip()
        if user_key:
            API_KEY = user_key

    # Prompt user for array of URLs
    urls_raw = input("\nEnter array of URLs (e.g., ['stripe.com', 'vercel.com'] or comma-separated): ").strip()
    
    # Safely parse the array
    if (urls_raw.startswith('[') and urls_raw.endswith(']')) or (urls_raw.startswith('(') and urls_raw.endswith(')')):
        try:
            urls = json.loads(urls_raw.replace("'", '"'))
        except Exception:
            urls = [u.strip().strip("'\"") for u in urls_raw[1:-1].split(",")]
    else:
        urls = [u.strip() for u in re.split(r'[,\s]+', urls_raw) if u.strip()]

    print(f"\nProcessing {len(urls)} website(s)...")
    results = []
    
    for url_to_enrich in urls:
        print(f"Enriching: {url_to_enrich}")
        result = enrich_company(url_to_enrich)
        results.append(result)
        
    print("\n" + "=" * 60)
    print("  FINAL OUT ARRAY OUTPUT (JSON)")
    print("=" * 60)
    print(json.dumps(results, indent=2))
    print("=" * 60)

    # Save to file
    with open("results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Saved results to 'results.json' successfully.")
