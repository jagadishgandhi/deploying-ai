"""
Module 1: Trader Joe's Product URL Scraper
Collects all product URLs from category listing pages
Saves to: data/product_urls.json (with auto-archival)
"""

import asyncio
import json
import random
import shutil
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright


class ProductURLScraper:
    """Scraper for collecting product URLs from listing pages"""

    def __init__(self, headless=False):
        """
        Initialize the URL scraper.

        Args:
            headless: If True, run browser in headless mode (no window)
        """
        self.headless = headless
        self.product_urls = []
        self.data_dir = Path(__file__).parent.parent / "data"
        self.output_file = self.data_dir / "product_urls.json"

    def archive_existing_file(self):
        """
        Archive existing product_urls.json if it exists.
        Archives to: product_urls_YYYYMMDD_HHMMSS.json
        """
        if self.output_file.exists():
            # Generate timestamp for archive
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"product_urls_{timestamp}.json"
            archive_path = self.data_dir / archive_name

            # Copy to archive
            shutil.copy2(self.output_file, archive_path)
            print(f"📦 Archived existing file to: {archive_name}")
            return archive_path
        return None

    async def scrape_urls(self):
        """
        Scrape all product URLs from Trader Joe's category listing pages.

        Returns:
            list: List of product URLs
        """
        print("="*60)
        print("MODULE 1: Collecting Product URLs")
        print("="*60)

        # Archive existing file before starting
        self.archive_existing_file()

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                viewport={'width': 1920, 'height': 1080}
            )

            # Anti-detection script
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)

            page = await context.new_page()

            # Start at the main products listing
            base_url = "https://www.traderjoes.com/home/products/category/products-2"
            page_num = 1
            max_pages = 1  # Safety limit (expected ~105)

            print(f"\nStarting URL collection from: {base_url}")
            print(f"Expected: ~1,573 products across ~105 pages")
            print("-"*60)

            while page_num <= max_pages:
                # Correct pagination format: ?filters=%7B%22page%22%3A2%7D
                # URL-encoded JSON: {"page":2}
                if page_num > 1:
                    url = f"{base_url}?filters=%7B%22page%22%3A{page_num}%7D"
                else:
                    url = base_url

                print(f"\nPage {page_num}: Scraping...")

                try:
                    # Navigate to page
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(random.uniform(1, 2))

                    # Wait for product links
                    await page.wait_for_selector('a[href*="/home/products/pdp/"]', timeout=10000)

                    # Extract product URLs from this page
                    urls = await page.evaluate("""
                        () => {
                            const links = Array.from(document.querySelectorAll('a[href*="/home/products/pdp/"]'));
                            const uniqueUrls = new Set();
                            links.forEach(link => uniqueUrls.add(link.href));
                            return Array.from(uniqueUrls);
                        }
                    """)

                    if not urls:
                        print(f"  No products found - reached end at page {page_num}")
                        break

                    print(f"  ✓ Found {len(urls)} product URLs")
                    self.product_urls.extend(urls)
                    print(f"  Total URLs collected: {len(self.product_urls)}")

                    # Continue to next page
                    page_num += 1

                    # Add delay between pages (human-like behavior)
                    await asyncio.sleep(random.uniform(2, 4))

                except Exception as e:
                    print(f"  ✗ Error on page {page_num}: {e}")
                    break

            await browser.close()

        # Remove duplicates
        unique_urls = list(set(self.product_urls))

        print(f"\n{'='*60}")
        print(f"✅ URL Collection Complete!")
        print(f"   Total unique product URLs: {len(unique_urls)}")
        print(f"{'='*60}")

        self.product_urls = unique_urls
        return self.product_urls

    def save_urls(self):
        """
        Save collected URLs to JSON file with metadata.

        Returns:
            Path: Path to saved file
        """
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Create URL tracking records
        url_records = []
        for i, url in enumerate(self.product_urls):
            url_records.append({
                'url': url,
                'product_id': f'tj_{i:04d}',
                'scraped': False,
                'error': None,
                'collected_at': datetime.now().isoformat()
            })

        # Save to file
        with open(self.output_file, 'w') as f:
            json.dump(url_records, f, indent=2)

        print(f"\n💾 Saved URL tracking to: {self.output_file}")
        print(f"   {len(url_records)} URLs ready for scraping")

        return self.output_file

    async def run(self):
        """
        Main execution flow: scrape URLs and save to file.

        Returns:
            Path: Path to saved URLs file
        """
        print("""
╔══════════════════════════════════════════════════════════╗
║      Trader Joe's Product URL Scraper (Module 1)        ║
╚══════════════════════════════════════════════════════════╝
""")

        # Scrape URLs
        urls = await self.scrape_urls()

        # Save to file
        output_path = self.save_urls()

        print(f"\n{'='*60}")
        print("📊 SUMMARY")
        print(f"{'='*60}")
        print(f"URLs collected: {len(urls)}")
        print(f"Output file: {output_path}")
        print(f"\n✅ Module 1 complete! Ready for Module 2 (scrape_product_details.py)")
        print(f"{'='*60}\n")

        return output_path


async def main():
    """Main entry point"""
    import sys

    headless = "--headless" in sys.argv

    scraper = ProductURLScraper(headless=headless)
    await scraper.run()


if __name__ == "__main__":
    print("""
Usage:
  python scrape_product_urls.py           # Run with visible browser
  python scrape_product_urls.py --headless # Run without browser window

Features:
  • Auto-archives existing product_urls.json before overwriting
  • Collects ~1,573 product URLs from 105 pages
  • Saves to: data/product_urls.json
  • Time: ~5-10 minutes

Next step: Run scrape_product_details.py to scrape product information
""")

    asyncio.run(main())
