import os
import time
import json
import hashlib
import logging
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError
from typing import Optional
from urllib.parse import urljoin
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIGURATION ---
BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
HEADERS = {'User-Agent': 'PoliteStudentBot/1.0 (Learning Project; FlyRank Assignment A9; student@example.com)'}
CACHE_DIR = "cache"
OUTPUT_DIR = "output"
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Analytics for run report
run_stats = {
    "start_time": datetime.now(timezone.utc).isoformat(),
    "duration_seconds": 0,
    "pages_fetched": 0,
    "cache_hits": 0,
    "valid_records": 0,
    "invalid_records": 0,
    "failed_pages": 0
}

# --- STAGE 4: SCHEMA ---
class BookRecord(BaseModel):
    title: str
    product_url: str
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: Optional[str]
    source_page: str
    fetched_at: str

# --- STAGE 1: FETCH AND CACHE ---
def get_cache_path(url: str) -> str:
    # Use MD5 hash of the URL to create a safe filename
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    return os.path.join(CACHE_DIR, f"{url_hash}.html")

def fetch_page(url: str) -> Optional[str]:
    cache_path = get_cache_path(url)
    
    # 1. Read from cache if it exists
    if os.path.exists(cache_path):
        run_stats["cache_hits"] += 1
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()

    # 2. Otherwise, fetch politely
    try:
        logging.info(f"FETCHING live page: {url}")
        time.sleep(0.5) # Minimum 500ms delay between requests
        
        response = requests.get(url, headers=HEADERS, timeout=10)
        # Raise error for 404, 500, etc.
        response.raise_for_status() 
        
        html_content = response.text
        
        # Save to cache
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        run_stats["pages_fetched"] += 1
        return html_content

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch {url}: {e}")
        run_stats["failed_pages"] += 1
        return None

# --- HELPER PARSERS ---
def parse_price(price_text: str) -> float:
    match = re.search(r'[\d\.]+', price_text)
    return float(match.group()) if match else 0.0

# --- MAIN SCRAPER ---
def main():
    start_time_obj = time.time()
    
    # --- STAGE 2: DISCOVER THREE CATALOGUE PAGES ---
    discovered_urls = {}
    current_url = BASE_URL
    pages_scraped = 0
    
    while current_url and pages_scraped < 3:
        logging.info(f"Processing catalogue page: {current_url}")
        html = fetch_page(current_url)
        if not html:
            break
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract book links
        articles = soup.find_all('article', class_='product_pod')
        for article in articles:
            relative_link = article.h3.a['href']
            absolute_link = urljoin(current_url, relative_link)
            # Use dictionary to guarantee uniqueness (no duplicates)
            discovered_urls[absolute_link] = current_url
            
        pages_scraped += 1
        
        # Find next page link
        next_button = soup.find('li', class_='next')
        if next_button and pages_scraped < 3:
            next_relative = next_button.a['href']
            current_url = urljoin(current_url, next_relative)
        else:
            current_url = None

    logging.info(f"Discovered {len(discovered_urls)} unique book URLs.")

    # --- STAGE 5: DELIBERATELY BROKEN URL ---
    # Inject a fake URL to prove we survive failures
    discovered_urls["https://books.toscrape.com/catalogue/this-is-a-fake-book_9999/index.html"] = "fake_source"

    # --- STAGE 3 & 4: EXTRACT, CLEAN, VALIDATE ---
    good_records = []
    bad_records = []

    for book_url, source_url in discovered_urls.items():
        html = fetch_page(book_url)
        if not html:
            # We log it, but continue the loop (surviving the broken page)
            continue
            
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            main_product = soup.find('div', class_='product_main')
            title = main_product.h1.text
            price_text = main_product.find('p', class_='price_color').text
            availability_text = main_product.find('p', class_='instock availability').text.strip()
            
            # Rating might be missing, parse carefully
            rating_p = main_product.find('p', class_='star-rating')
            rating_text = rating_p['class'][1] if rating_p else "Unknown"
            
            # Description is sometimes missing
            desc_div = soup.find('div', id='product_description')
            description = desc_div.find_next_sibling('p').text if desc_div else None
            
            # Assemble raw fields
            raw_data = {
                "title": title,
                "product_url": book_url,
                "price_text": price_text,
                "price_gbp": parse_price(price_text),
                "availability_text": availability_text,
                "rating_text": rating_text,
                "description": description,
                "source_page": source_url,
                "fetched_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Validate against Pydantic schema
            validated_record = BookRecord(**raw_data)
            good_records.append(validated_record.model_dump())
            run_stats["valid_records"] += 1
            
        except ValidationError as ve:
            logging.warning(f"Validation failed for {book_url}")
            bad_records.append({"url": book_url, "error": str(ve)})
            run_stats["invalid_records"] += 1
        except Exception as e:
            logging.error(f"Extraction error on {book_url}: {e}")
            bad_records.append({"url": book_url, "error": str(e)})
            run_stats["invalid_records"] += 1

    # --- SAVE OUTPUTS ---
    with open(os.path.join(OUTPUT_DIR, 'books.json'), 'w', encoding='utf-8') as f:
        json.dump(good_records, f, indent=4, ensure_ascii=False)
        
    if bad_records:
        with open(os.path.join(OUTPUT_DIR, 'errors.json'), 'w', encoding='utf-8') as f:
            json.dump(bad_records, f, indent=4)
            
    # --- STAGE 5: RUN REPORT ---
    run_stats["duration_seconds"] = round(time.time() - start_time_obj, 2)
    with open(os.path.join(OUTPUT_DIR, 'run-report.json'), 'w', encoding='utf-8') as f:
        json.dump(run_stats, f, indent=4)
        
    logging.info(f"Run complete. Valid: {len(good_records)}. Failed pages: {run_stats['failed_pages']}.")

if __name__ == "__main__":
    main()
