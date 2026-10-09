# FlyRank - The Polite Scraper (A9)

## 0. Target Classification
- **Site:** `http://books.toscrape.com`
- **Why:** The site clearly states on its homepage that it is a sandbox built for scraping practice.
- **Scope:** First 3 catalogue pages.
- **Data Collected:** Book title, product URL, price, availability, rating, and description.
- **Appropriateness:** This is exactly the data a sandbox site intends for users to scrape safely without impacting real businesses.
- **Robots.txt:** I checked `https://books.toscrape.com/robots.txt`. The file does not exist (returns a 404 error). A missing file is not permission, but given the site's explicit text permission, it is safe to proceed.
- **Ethics Statement:** I will not reuse this code on another site without checking its rules and terms first. Use an official API when one exists; never bypass logins, paywalls, or blocks; collect only what you need.

## 1. Quick Start
To install dependencies and run the scraper in under 5 minutes:
```bash
# Python Lane
cd book_scraper
pip install -r requirements.txt
python scraper.py
```

## 2. Politeness Rules Followed
- **User-Agent:** Sends a custom, identifying User-Agent (`PoliteStudentBot/1.0`).
- **Delay:** Minimum 500ms sleep between live requests to never hammer the server.
- **Timeout:** 10-second timeout on all requests.
- **Cache:** Saves all fetched HTML to `/cache/` and reads from it on reruns to spare the server.

## 3. Data Schema
Every record is validated against this Pydantic schema before storage:
- `title` (String)
- `product_url` (String)
- `price_text` (String, original)
- `price_gbp` (Float, cleaned)
- `availability_text` (String)
- `rating_text` (String)
- `description` (String, Optional)
- `source_page` (String)
- `fetched_at` (String/ISO 8601 Date)

## 4. Run Report Proof
*Sample `output/run-report.json` after running:*
```json
{
    "start_time": "2026-10-09T11:51:00.000000+00:00",
    "duration_seconds": 2.54,
    "pages_fetched": 0,
    "cache_hits": 63,
    "valid_records": 60,
    "invalid_records": 0,
    "failed_pages": 1
}
```
*(Notice the `failed_pages: 1` — this is a deliberately injected fake URL to prove the pipeline survives a 404 without crashing).*

## 5. Limitations & Browser Note
- **Limitation:** The scraper assumes prices are always formatted with numerical digits following the currency symbol. If the site format dramatically changes, the regex might fail.
- **Why No Browser?** We used standard HTTP requests instead of a headless browser (like Playwright). This is because all data is embedded directly in the server-rendered HTML. A browser would add massive unnecessary cost, memory, and latency for no extra value.
