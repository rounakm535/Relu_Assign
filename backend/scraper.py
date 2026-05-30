import re
import random
import asyncio
from typing import List, Dict, Set, Any
from urllib.parse import urlparse, urljoin
import httpx
from bs4 import BeautifulSoup

# Rotated User-Agents to prevent blocking
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edge/119.0.0.0",
]

# Keywords to identify relevant pages
RELEVANT_KEYWORDS = ["about", "contact", "service", "solution", "product", "company", "team", "who-we-are"]

def get_random_headers() -> Dict[str, str]:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

def normalize_url(url: str) -> str:
    """Ensure url has a scheme (https:// by default)."""
    url = url.strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    return url

async def fetch_page(client: httpx.AsyncClient, url: str, retries: int = 3, backoff: float = 1.0) -> Optional[str]:
    """Fetch web page with retry logic and exponential backoff."""
    for attempt in range(retries):
        try:
            headers = get_random_headers()
            response = await client.get(url, headers=headers, timeout=10.0, follow_redirects=True)
            if response.status_code == 200:
                return response.text
            # Handle rate limiting (e.g. 429) or other errors by backing off
            if response.status_code == 429:
                await asyncio.sleep(backoff * (2 ** attempt))
            else:
                await asyncio.sleep(0.5)
        except Exception:
            await asyncio.sleep(backoff * (2 ** attempt))
    return None

def extract_sitemap_urls(robots_txt: str) -> List[str]:
    """Parse robots.txt to look for Sitemap declarations."""
    sitemaps = []
    if not robots_txt:
        return sitemaps
    for line in robots_txt.splitlines():
        if line.lower().startswith("sitemap:"):
            parts = line.split(":", 1)
            if len(parts) > 1:
                sitemaps.append(parts[1].strip())
    return sitemaps

def parse_sitemap_xml(xml_content: str) -> List[str]:
    """Parse sitemap XML to extract loc URLs."""
    urls = []
    if not xml_content:
        return urls
    # Clean XML content from namespace prefixes if necessary, or let bs4 handle it
    soup = BeautifulSoup(xml_content, "xml")
    loc_tags = soup.find_all("loc")
    for loc in loc_tags:
        if loc.text:
            urls.append(loc.text.strip())
    return urls

def clean_html(html_content: str) -> tuple[str, str]:
    """
    Remove headers, navbars, footers, scripts, styles, SVGs, cookie banners.
    Returns: (cleaned_text, raw_text_for_regex)
    """
    if not html_content:
        return "", ""

    soup = BeautifulSoup(html_content, "html.parser")
    raw_text = soup.get_text()

    # Elements to remove
    for tag in ["script", "style", "svg", "noscript", "iframe", "header", "footer", "nav"]:
        for element in soup.find_all(tag):
            element.decompose()

    # Common elements related to headers, footers, popups, cookie consent
    selectors = [
        "*[id*='cookie']", "*[class*='cookie']", 
        "*[id*='banner']", "*[class*='banner']",
        "*[id*='popup']", "*[class*='popup']",
        "*[id*='modal']", "*[class*='modal']",
        "*[id*='navbar']", "*[class*='navbar']",
        "*[id*='footer']", "*[class*='footer']",
        "*[id*='header']", "*[class*='header']"
    ]
    for selector in selectors:
        try:
            for element in soup.select(selector):
                element.decompose()
        except Exception:
            pass

    # Extract text and compress whitespaces
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    
    return text, raw_text

def extract_emails(text: str) -> List[str]:
    """Extract emails using regex and exclude common false positives like images."""
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}"
    raw_emails = re.findall(email_pattern, text)
    
    valid_emails = set()
    invalid_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tiff", ".pdf", ".zip", ".gz"}
    
    for email in raw_emails:
        email_lower = email.lower()
        # Ensure it doesn't end with common image/asset extensions
        if not any(email_lower.endswith(ext) for ext in invalid_extensions):
            # Basic validation
            if len(email_lower) > 5 and "." in email_lower.split("@")[-1]:
                valid_emails.add(email)
                
    return list(valid_emails)

def extract_phones(text: str) -> List[str]:
    """Extract phone numbers using regex."""
    # Matches international format: +1234567890, +1 123-456-7890, (123) 456-7890, etc.
    phone_pattern = r"\+?\d{1,4}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{2,4}"
    raw_phones = re.findall(phone_pattern, text)
    
    valid_phones = set()
    for phone in raw_phones:
        # Strip spaces and special characters to count actual digits
        digits = re.sub(r"\D", "", phone)
        # Phone numbers typically have between 7 and 15 digits
        if 7 <= len(digits) <= 15:
            # Clean up leading/trailing dashes or spaces
            cleaned = phone.strip(" -.")
            # Exclude obvious numbers (e.g. sequence of identical numbers, zip codes, coordinates)
            if not re.match(r"^(\d)\1+$", digits) and not (len(digits) == 5 and digits.startswith("0")):
                valid_phones.add(cleaned)
                
    return list(valid_phones)

def extract_address(text: str) -> str:
    """Extract physical address indicators from text."""
    # Look for patterns starting with Address/HQ/Headquarters and grabbing the line or next lines
    patterns = [
        r"(?:address|hq|headquarters|office|location)\s*:\s*([^.\n]{10,100})",
        r"(?:located\s+at|visit\s+us\s+at)\s*([^.\n]{10,100})"
    ]
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            addr = match.group(1).strip()
            # Verify if it has common address markers
            if any(marker in addr.lower() for marker in ["street", "st", "road", "rd", "ave", "boulevard", "blvd", "lane", "ln", "way", "suite", "ste", "floor", "building", "bldg", "drive", "dr", "highway", "hwy", "plaza", "block", "city", "state", "zip", "postal"]):
                return addr

    # Fallback to searching lines with postal/zip codes and city names
    # Match standard US zip code or international postal codes
    zip_pattern = r"\b\d{5}(?:-\d{4})?\b|\b[A-Za-z]\d[A-Za-z] \d[A-Za-z]\d\b"
    matches = list(re.finditer(zip_pattern, text))
    if matches:
        # Return a window around the first match
        first_match = matches[0]
        start = max(0, first_match.start() - 60)
        end = min(len(text), first_match.end() + 20)
        addr_segment = text[start:end].strip()
        # Clean segment
        lines = addr_segment.split(",")
        if len(lines) > 1:
            return ", ".join([line.strip() for line in lines[-3:] if len(line.strip()) > 3])
            
    return ""

async def scrape_company_website(url: str) -> Dict[str, Any]:
    """
    Intelligently scrapes a company's website to gather content.
    Fulfills Priority 1 (sitemap), Priority 2 (homepage crawling), Priority 3 (fallback URLs).
    Returns a dictionary with consolidated text, emails, phones, and address.
    """
    url = normalize_url(url)
    domain_parsed = urlparse(url)
    base_url = f"{domain_parsed.scheme}://{domain_parsed.netloc}"

    scraped_text_list = []
    all_emails = set()
    all_phones = set()
    all_addresses = set()
    visited_urls = set()

    async with httpx.AsyncClient(verify=False) as client:
        # 1. Scraping Sitemap (Priority 1)
        sitemap_urls = []
        try:
            # Check robots.txt first
            robots_content = await fetch_page(client, urljoin(base_url, "/robots.txt"))
            if robots_content:
                sitemap_urls = extract_sitemap_urls(robots_content)
            
            # If no sitemaps found in robots.txt, try default location
            if not sitemap_urls:
                sitemap_urls = [urljoin(base_url, "/sitemap.xml")]

            for sitemap_url in sitemap_urls:
                xml_content = await fetch_page(client, sitemap_url)
                if xml_content:
                    parsed_urls = parse_sitemap_xml(xml_content)
                    if parsed_urls:
                        # Filter to get relevant URLs
                        sitemap_urls = [
                            u for u in parsed_urls 
                            if any(kw in u.lower() for kw in RELEVANT_KEYWORDS)
                            and urlparse(u).netloc == domain_parsed.netloc
                        ]
                        break
        except Exception:
            pass

        # 2. Scrape Homepage (Priority 2)
        homepage_content = await fetch_page(client, base_url)
        homepage_links = []
        if homepage_content:
            visited_urls.add(base_url)
            clean_txt, raw_txt = clean_html(homepage_content)
            scraped_text_list.append(f"--- Homepage Content ---\n{clean_txt}")
            
            # Extract contacts from homepage
            all_emails.update(extract_emails(raw_txt))
            all_phones.update(extract_phones(raw_txt))
            addr = extract_address(raw_txt)
            if addr:
                all_addresses.add(addr)

            # Crawl links on homepage
            try:
                soup = BeautifulSoup(homepage_content, "html.parser")
                for link in soup.find_all("a", href=True):
                    href = link["href"].strip()
                    full_link = urljoin(base_url, href)
                    parsed_link = urlparse(full_link)
                    
                    # Ensure same domain and not visited and fits keywords
                    if (parsed_link.netloc == domain_parsed.netloc 
                        and full_link not in visited_urls 
                        and any(kw in full_link.lower() for kw in RELEVANT_KEYWORDS)):
                        homepage_links.append(full_link)
            except Exception:
                pass

        # 3. Consolidate target pages to crawl
        target_pages = []
        if sitemap_urls:
            target_pages.extend(sitemap_urls)
        if homepage_links:
            target_pages.extend(homepage_links)

        # Remove duplicates and homepage
        target_pages = list(set(target_pages) - visited_urls)

        # Fallback (Priority 3) - if we have no links, guess them
        if not target_pages:
            guess_paths = [
                "/about", "/about-us", "/services", "/solutions",
                "/products", "/contact", "/contact-us", "/company"
            ]
            target_pages = [urljoin(base_url, path) for path in guess_paths]

        # Select up to 4 most promising pages to scrape (prefer contact, about, services)
        def page_priority(u: str) -> int:
            u_lower = u.lower()
            if "contact" in u_lower:
                return 0
            if "about" in u_lower or "company" in u_lower or "who-we-are" in u_lower:
                return 1
            if "service" in u_lower or "solution" in u_lower or "product" in u_lower:
                return 2
            return 3

        target_pages.sort(key=page_priority)
        target_pages = target_pages[:4]  # Scrape at most 4 subpages to limit tokens/time

        # Fetch subpages concurrently
        async def process_subpage(subpage_url: str):
            if subpage_url in visited_urls:
                return
            visited_urls.add(subpage_url)
            content = await fetch_page(client, subpage_url)
            if content:
                clean_txt, raw_txt = clean_html(content)
                scraped_text_list.append(f"--- Page: {subpage_url} ---\n{clean_txt}")
                all_emails.update(extract_emails(raw_txt))
                all_phones.update(extract_phones(raw_txt))
                addr = extract_address(raw_txt)
                if addr:
                    all_addresses.add(addr)

        await asyncio.gather(*(process_subpage(u) for u in target_pages), return_exceptions=True)

    # Compile findings
    consolidated_text = "\n\n".join(scraped_text_list)
    # Token optimization: Limit context length to around 12,000 characters (~3000 tokens)
    if len(consolidated_text) > 12000:
        consolidated_text = consolidated_text[:12000] + "... [Text Truncated for token limit]"

    # Resolve address (pick the longest one, or empty)
    address_final = max(all_addresses, key=len) if all_addresses else ""
    mobile_final = sorted(list(all_phones))[0] if all_phones else ""
    mail_final = list(all_emails)

    return {
        "domain": domain_parsed.netloc,
        "scraped_text": consolidated_text,
        "emails": mail_final,
        "phones": mobile_final,
        "address": address_final,
    }
