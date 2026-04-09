#!/usr/bin/env python3
"""
Generates a JSON file of all site pages with titles and H1s for internal linking.
Uses Decodo Web Scraping API to fetch sitemap and scrape pages.
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests

# Configuration
SITEMAP_URL = "https://decodo.com/sitemap-0.xml"
DECODO_API_URL = "https://scraper-api.decodo.com/v2/scrape"
DELAY_BETWEEN_REQUESTS = 1.0  # seconds between requests (be respectful)
OUTPUT_FILE = "data/internal-links.json"

# URL patterns to categorize pages (customize for your site)
URL_PATTERNS = {
    "blog": ["/blog/", "/devs/"],
    "product": ["/proxies/", "/scraping-api/", "/unblocker/"],
    "tool": ["/tools/"],
    "docs": ["/docs/", "/help/"],
    "landing": ["/use-case/", "/industry/"],
    "legal": ["/legal/", "/privacy/", "/terms/"],
}


def get_api_token():
    """Get API token from environment variable."""
    token = os.environ.get("DECODO_API_TOKEN")
    if not token:
        raise ValueError("DECODO_API_TOKEN environment variable not set")
    return token


def scrape_url(url: str, token: str) -> dict | None:
    """Scrape a URL using Decodo Web Scraping API."""
    headers = {
        "Accept": "application/json",
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }
    
    # Simple payload - just the URL, no extra parameters
    payload = {
        "url": url,
    }
    
    try:
        response = requests.post(
            DECODO_API_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        # Log the response for debugging if it fails
        if not response.ok:
            print(f"  API Error {response.status_code}: {response.text[:500]}")
            return None
            
        return response.json()
    except requests.RequestException as e:
        print(f"  Request error for {url}: {e}")
        return None


def extract_from_html(html: str) -> dict:
    """Extract title and H1 from HTML content."""
    result = {"title": None, "h1": None}
    
    # Extract title
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if title_match:
        result["title"] = title_match.group(1).strip()
    
    # Extract first H1
    h1_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html, re.IGNORECASE | re.DOTALL)
    if h1_match:
        # Clean up the H1 (remove extra whitespace, HTML entities)
        h1_text = h1_match.group(1).strip()
        h1_text = re.sub(r"\s+", " ", h1_text)
        h1_text = h1_text.replace("&amp;", "&").replace("&nbsp;", " ")
        result["h1"] = h1_text
    
    # If no simple H1 found, try with nested tags
    if not result["h1"]:
        h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        if h1_match:
            # Strip all HTML tags from inside H1
            h1_text = re.sub(r"<[^>]+>", "", h1_match.group(1))
            h1_text = re.sub(r"\s+", " ", h1_text).strip()
            result["h1"] = h1_text if h1_text else None
    
    return result


def categorize_url(url: str) -> str:
    """Determine the category of a URL based on its path."""
    path = urlparse(url).path.lower()
    
    for category, patterns in URL_PATTERNS.items():
        for pattern in patterns:
            if pattern in path:
                return category
    
    # Default category for uncategorized pages
    return "other"


def parse_sitemap(xml_content: str) -> list[str]:
    """Parse sitemap XML and extract URLs."""
    # Simple regex-based parsing (works for standard sitemaps)
    urls = re.findall(r"<loc>([^<]+)</loc>", xml_content)
    return urls


def fetch_sitemap_direct(url: str) -> str:
    """Fetch sitemap directly (no need for Decodo - it's public XML)."""
    try:
        response = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (compatible; InternalLinkBot/1.0)"
        })
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"  Error fetching sitemap: {e}")
        return ""


def main():
    print(f"Starting internal links generation at {datetime.now(timezone.utc).isoformat()}")
    
    token = get_api_token()
    print(f"Token loaded (length: {len(token)} chars)")
    
    # Step 1: Fetch sitemap directly (public XML, no scraping needed)
    print(f"\n1. Fetching sitemap: {SITEMAP_URL}")
    sitemap_content = fetch_sitemap_direct(SITEMAP_URL)
    
    if not sitemap_content:
        raise RuntimeError("Failed to fetch sitemap")
    
    print(f"   Sitemap fetched ({len(sitemap_content)} bytes)")
    
    urls = parse_sitemap(sitemap_content)
    print(f"   Found {len(urls)} URLs in sitemap")
    
    if not urls:
        print(f"   Sitemap content preview: {sitemap_content[:500]}")
        raise RuntimeError("No URLs found in sitemap - check sitemap format")
    
    # Step 2: Scrape each URL
    print(f"\n2. Scraping pages for titles and H1s...")
    pages = []
    errors = []
    
    for i, url in enumerate(urls, 1):
        print(f"   [{i}/{len(urls)}] {url}")
        
        response = scrape_url(url, token)
        
        if response and "results" in response and response["results"]:
            html_content = response["results"][0].get("content", "")
            extracted = extract_from_html(html_content)
            
            page_data = {
                "url": url,
                "path": urlparse(url).path,
                "title": extracted["title"],
                "h1": extracted["h1"],
                "category": categorize_url(url),
            }
            pages.append(page_data)
            print(f"       ✓ Title: {extracted['title'][:50] if extracted['title'] else 'N/A'}...")
        else:
            errors.append({"url": url, "error": "Failed to scrape"})
            print(f"       ✗ Failed")
        
        # Rate limiting
        if i < len(urls):
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # Step 3: Build output structure
    print(f"\n3. Building JSON output...")
    
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_pages": len(pages),
        "sitemap_url": SITEMAP_URL,
        "pages": pages,
        "errors": errors,
        "categories": {}
    }
    
    # Group by category for easier lookup
    for page in pages:
        cat = page["category"]
        if cat not in output["categories"]:
            output["categories"][cat] = []
        output["categories"][cat].append(page["url"])
    
    # Step 4: Write output
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n4. Done! Output written to {OUTPUT_FILE}")
    print(f"   Total pages: {len(pages)}")
    print(f"   Errors: {len(errors)}")
    print(f"   Categories: {list(output['categories'].keys())}")


if __name__ == "__main__":
    main()
