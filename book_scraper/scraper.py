import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError
import time
import json
import logging
import re

# Set up logging to show we are surviving errors gracefully
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define Schema for Data Validation (turns messy data into clean, checked rules)
class Book(BaseModel):
    title: str
    price: float
    availability: bool
    rating: int

# Custom polite headers (telling the server who we are, as a professional does)
HEADERS = {
    'User-Agent': 'PoliteStudentBot/1.0 (Learning Project; FlyRank Assignment)'
}

def parse_price(price_str: str) -> float:
    # Extracts real number from messy text like "£51.77" or "Â£51.77"
    match = re.search(r'[\d\.]+', price_str)
    if match:
        return float(match.group())
    return 0.0

def parse_rating(class_list: list) -> int:
    # Converts text-based star ratings into integers
    ratings = {'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5}
    for c in class_list:
        if c in ratings:
            return ratings[c]
    return 0

def scrape_page(url: str):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        # Check if the page broke or gave a bad status code (e.g., 404, 500)
        response.raise_for_status() 
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return None

def main():
    # The famous free practice site
    base_url = "http://books.toscrape.com/catalogue/page-{}.html"
    all_valid_books = []
    total_pages = 3  # Collecting exactly 60 books (20 per page * 3 pages)

    for page_num in range(1, total_pages + 1):
        url = base_url.format(page_num)
        logging.info(f"Scraping page {page_num}...")
        
        html_content = scrape_page(url)
        if not html_content:
            logging.warning(f"Skipping page {page_num} due to errors. (Surviving a broken page)")
            continue
            
        soup = BeautifulSoup(html_content, 'html.parser')
        book_articles = soup.find_all('article', class_='product_pod')

        for article in book_articles:
            try:
                title = article.h3.a['title']
                price_text = article.find('p', class_='price_color').text
                price = parse_price(price_text)
                
                # Check stock availability
                instock_text = article.find('p', class_='instock availability').text.strip()
                availability = "In stock" in instock_text
                
                # Extract rating
                rating_p = article.find('p', class_='star-rating')
                rating = parse_rating(rating_p.get('class', [])) if rating_p else 0
                
                # Validate every record against our Pydantic schema
                book_data = {
                    "title": title,
                    "price": price,
                    "availability": availability,
                    "rating": rating
                }
                valid_book = Book(**book_data)
                all_valid_books.append(valid_book.model_dump())
                
            except ValidationError as ve:
                logging.error(f"Data validation failed for a book: {ve}")
            except Exception as e:
                logging.error(f"Unexpected error parsing a book on page {page_num}: {e}")
                
        # The ultimate polite rule: Go slowly. Never hammer a server.
        time.sleep(2)
        
    # Write cleanly checked data to JSON
    with open('books.json', 'w', encoding='utf-8') as f:
        json.dump(all_valid_books, f, indent=4, ensure_ascii=False)
        
    logging.info(f"✅ Successfully scraped, validated, and saved {len(all_valid_books)} books to books.json")

if __name__ == "__main__":
    main()
