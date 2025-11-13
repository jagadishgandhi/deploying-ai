"""
Module 2: Trader Joe's Product Details Scraper
Scrapes comprehensive product details from URLs collected by Module 1
Extracts: name, price, description, ingredients, nutrition, allergens, tags
Saves to: data/tj_products_full.json (with auto-archival)
"""

import asyncio
import json
import random
import shutil
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright


class ProductDetailsScraper:
    """Scraper for collecting detailed product information"""

    def __init__(self, headless=False):
        """
        Initialize the product details scraper.

        Args:
            headless: If True, run browser in headless mode (no window)
        """
        self.headless = headless
        self.products = []
        self.data_dir = Path(__file__).parent.parent / "data"
        self.urls_file = self.data_dir / "product_urls.json"
        self.output_file = self.data_dir / "tj_products_full.json"

    def archive_existing_file(self):
        """
        Archive existing tj_products_full.json if it exists.
        Archives to: tj_products_full_YYYYMMDD_HHMMSS.json
        """
        if self.output_file.exists():
            # Generate timestamp for archive
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"tj_products_full_{timestamp}.json"
            archive_path = self.data_dir / archive_name

            # Copy to archive
            shutil.copy2(self.output_file, archive_path)
            print(f"📦 Archived existing file to: {archive_name}")
            return archive_path
        return None

    def load_urls(self, resume=False):
        """
        Load URLs from product_urls.json.

        Args:
            resume: If True, only load un-scraped URLs

        Returns:
            list: List of URL records to scrape
        """
        if not self.urls_file.exists():
            raise FileNotFoundError(
                f"URL file not found: {self.urls_file}\n"
                f"Please run scrape_product_urls.py first (Module 1)"
            )

        with open(self.urls_file, 'r') as f:
            url_records = json.load(f)

        if resume:
            # Filter to only un-scraped URLs
            urls_to_scrape = [r for r in url_records if not r.get('scraped', False)]
            print(f"📂 Resume mode: {len(urls_to_scrape)} un-scraped URLs")
        else:
            # Reset all URLs to un-scraped
            for record in url_records:
                record['scraped'] = False
                record['error'] = None
            urls_to_scrape = url_records
            print(f"📂 Fresh start: {len(urls_to_scrape)} total URLs")

        return url_records, urls_to_scrape

    async def scrape_product_details(self, url_record):
        """
        Scrape detailed information from a single product page.

        Args:
            url_record: URL record dict with 'url' and 'product_id'

        Returns:
            dict: Product details
        """
        url = url_record['url']
        product_id = url_record['product_id']

        # This will be populated by page.evaluate()
        product = await self.page.evaluate("""
            () => {
                // Product name
                const nameEl = document.querySelector('h1.ProductDetails_main__title__14Cnm') ||
                              document.querySelector('h1');
                const name = nameEl?.textContent?.trim() || 'Unknown';

                // Price and unit
                let price = null;
                let unit = '';
                const priceEl = document.querySelector('.ProductPrice_productPrice__price__3-50j');
                if (priceEl) {
                    const priceMatch = priceEl.textContent.match(/\\$?([0-9]+\\.?[0-9]*)/);
                    if (priceMatch) price = parseFloat(priceMatch[1]);
                }

                const unitEl = document.querySelector('.ProductPrice_productPrice__unit__2jvkA');
                if (unitEl) {
                    unit = unitEl.textContent.trim().replace(/^\\//, '');
                }

                // Default price if not found
                if (!price) price = 3.99;

                // Category and subcategory from breadcrumbs
                const breadcrumbs = Array.from(document.querySelectorAll('.Breadcrumbs_list__link__rcn9k'));
                const category = breadcrumbs.length > 0 ?
                    breadcrumbs[breadcrumbs.length - 1]?.textContent?.trim() : 'Food';
                const subcategory = breadcrumbs.length > 1 ?
                    breadcrumbs[breadcrumbs.length - 2]?.textContent?.trim() : '';

                // Description
                let description = '';
                const descContainer = document.querySelector('.ProductDetails_main__description__2R7nN .Expand_expand__container__3COzO');
                if (descContainer) {
                    const paragraphs = Array.from(descContainer.querySelectorAll('p'));
                    const texts = paragraphs
                        .map(p => p.textContent.trim())
                        .filter(text => text && text.length > 0);
                    description = texts.join(' ');
                }

                // "We Love This For" tags
                const tags = [];
                const tagElements = document.querySelectorAll('.FunTag_tag__text__1FfQ6');
                tagElements.forEach(el => {
                    const tag = el.textContent.trim();
                    if (tag) tags.push(tag);
                });

                // Ingredients and allergens
                let ingredients = '';
                let allergens_contains = [];
                let allergens_may_contain = [];

                const ingredientsEl = document.querySelector('.IngredientsSummary_ingredientsSummary__1WMGh');
                if (ingredientsEl) {
                    // Get main ingredients from <li> elements in IngredientsList
                    const ingredientsList = ingredientsEl.querySelector('.IngredientsList_ingredientsList__1LoAJ');
                    if (ingredientsList) {
                        const ingredientItems = Array.from(ingredientsList.querySelectorAll('li'));
                        ingredients = ingredientItems
                            .map(li => li.textContent.trim())
                            .filter(text => text)
                            .join(' ');
                    }

                    // If no structured list found, try text nodes as fallback
                    if (!ingredients) {
                        const textNodes = Array.from(ingredientsEl.childNodes)
                            .filter(node => node.nodeType === Node.TEXT_NODE)
                            .map(node => node.textContent.trim())
                            .filter(text => text && !text.startsWith('CONTAINS') && !text.startsWith('MAY CONTAIN'));
                        ingredients = textNodes.join(' ');
                    }

                    // Get allergens - handle both "CONTAINS" and "MAY CONTAIN"
                    const allergenItems = ingredientsEl.querySelectorAll('.IngredientsSummary_ingredientsSummary__allergensListItem__2LBiz');
                    allergenItems.forEach(item => {
                        const text = item.textContent.trim();
                        if (text.startsWith('CONTAINS')) {
                            const allergenList = text.replace('CONTAINS', '').trim().replace(/\.$/, '');
                            allergens_contains = allergenList.split(',').map(a => a.trim());
                        } else if (text.startsWith('MAY CONTAIN')) {
                            const allergenList = text.replace('MAY CONTAIN', '').trim().replace(/\.$/, '');
                            allergens_may_contain = allergenList.split(',').map(a => a.trim());
                        }
                    });
                }

                // Nutrition facts (only for Food and Beverages)
                const nutrition = {};
                const nutritionTable = document.querySelector('.Item_table__2PMbE tbody');
                if (nutritionTable) {
                    // Get serving info
                    const servingEl = document.querySelector('.Item_characteristics__text__dcfEC');
                    if (servingEl) {
                        nutrition.serving_size = servingEl.textContent.trim();
                    }

                    // Get servings per container
                    const servingsText = document.querySelector('.Item_characteristics__title__7nfa8');
                    if (servingsText && servingsText.textContent.includes('Serves about')) {
                        const servingsMatch = servingsText.textContent.match(/Serves about ([0-9.]+)/);
                        if (servingsMatch) nutrition.servings_per_container = parseFloat(servingsMatch[1]);
                    }

                    // Get calories
                    const caloriesEl = document.querySelectorAll('.Item_characteristics__text__dcfEC')[1];
                    if (caloriesEl) {
                        const calMatch = caloriesEl.textContent.match(/([0-9]+)/);
                        if (calMatch) nutrition.calories = parseInt(calMatch[1]);
                    }

                    // Parse nutrition table
                    const rows = nutritionTable.querySelectorAll('tr');
                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 2) {
                            const nutrient = cells[0].textContent.trim();
                            const amount = cells[1].textContent.trim();

                            // Map nutrients to consistent field names
                            const nutrientMap = {
                                'Total Fat': 'total_fat_g',
                                'Saturated Fat': 'saturated_fat_g',
                                'Trans Fat': 'trans_fat_g',
                                'Cholesterol': 'cholesterol_mg',
                                'Sodium': 'sodium_mg',
                                'Total Carbohydrate': 'total_carbohydrate_g',
                                'Dietary Fiber': 'dietary_fiber_g',
                                'Total Sugars': 'total_sugars_g',
                                'Protein': 'protein_g',
                                'Vitamin D': 'vitamin_d_mcg',
                                'Calcium': 'calcium_mg',
                                'Iron': 'iron_mg',
                                'Potassium': 'potassium_mg',
                                'Added Sugars': 'added_sugars_g'
                            };

                            if (nutrientMap[nutrient]) {
                                const numMatch = amount.match(/([0-9.]+)/);
                                if (numMatch) {
                                    nutrition[nutrientMap[nutrient]] = parseFloat(numMatch[1]);
                                }
                            }
                        }
                    });
                }

                // Check if limited time product
                const limitedTime = document.querySelector('.Carousel_tape__text__t5-Wy')?.textContent?.includes('LIMITED TIME') || false;

                return {
                    name: name,
                    price: price,
                    unit: unit,
                    category: category,
                    subcategory: subcategory,
                    description: description.substring(0, 1000),
                    tags: tags,
                    ingredients: ingredients,
                    allergens_contains: allergens_contains,
                    allergens_may_contain: allergens_may_contain,
                    nutrition: Object.keys(nutrition).length > 0 ? nutrition : null,
                    limited_time: limitedTime,
                    url: window.location.href
                };
            }
        """)

        # Add product ID and scrape timestamp
        product['id'] = product_id
        product['scraped_at'] = datetime.now().isoformat()

        return product

    async def scrape_all(self, limit=None, resume=False):
        """
        Scrape details from all URLs.

        Args:
            limit: Optional limit on number of products (for testing)
            resume: If True, skip already-scraped URLs

        Returns:
            list: List of scraped products
        """
        print(f"\n{'='*60}")
        print("MODULE 2: Scraping Product Details")
        print(f"{'='*60}")

        # Archive existing file before starting
        self.archive_existing_file()

        # Load URLs
        url_records, urls_to_scrape = self.load_urls(resume=resume)

        # Apply limit if specified
        if limit:
            urls_to_scrape = urls_to_scrape[:limit]

        total = len(urls_to_scrape)
        print(f"Scraping {total} products...")
        print("-"*60)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                viewport={'width': 1920, 'height': 1080}
            )

            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)

            self.page = await context.new_page()

            for i, url_record in enumerate(urls_to_scrape, 1):
                url = url_record['url']
                product_id = url_record['product_id']
                print(f"\n[{i}/{total}] {product_id}: {url[:60]}...")

                # Retry logic with exponential backoff
                max_retries = 3
                retry_count = 0
                last_error = None
                scraped_successfully = False

                while retry_count < max_retries and not scraped_successfully:
                    try:
                        if retry_count > 0:
                            wait_time = min(5 * (2 ** (retry_count - 1)), 30)
                            print(f"  ⏰ Retry {retry_count}/{max_retries} after {wait_time}s...")
                            await asyncio.sleep(wait_time)

                        # Navigate to product page with better wait strategy
                        await self.page.goto(url, wait_until='networkidle', timeout=30000)

                        # Wait for critical elements
                        try:
                            await self.page.wait_for_selector('h1.ProductDetails_main__title__14Cnm', timeout=10000)
                        except:
                            await self.page.wait_for_selector('h1', timeout=5000)

                        # Human-like delay after page load
                        await asyncio.sleep(random.uniform(1.5, 3.0))

                        # Extract product details
                        product = await self.scrape_product_details(url_record)

                        self.products.append(product)
                        print(f"  ✓ {product['name']}: ${product['price']}")

                        # Show data completeness
                        has_ingredients = bool(product.get('ingredients'))
                        has_nutrition = bool(product.get('nutrition'))
                        has_allergens_contains = len(product.get('allergens_contains', [])) > 0
                        has_allergens_may = len(product.get('allergens_may_contain', [])) > 0
                        has_tags = len(product.get('tags', [])) > 0
                        print(f"    Data: ingredients={has_ingredients}, nutrition={has_nutrition}, allergens={has_allergens_contains}/{has_allergens_may}, tags={has_tags}")

                        # Mark successful scrape
                        scraped_successfully = True
                        url_record['scraped'] = True
                        url_record['error'] = None
                        url_record['scraped_at'] = datetime.now().isoformat()

                        # Save progress every 50 products
                        if i % 50 == 0:
                            self.save_products(temp=True)
                            self.update_tracking(url_records)
                            print(f"  💾 Progress saved ({i}/{total})")

                    except TimeoutError as e:
                        last_error = f"Timeout: {str(e)}"
                        retry_count += 1
                        if retry_count >= max_retries:
                            print(f"  ✗ Failed after {max_retries} retries - Timeout")
                            url_record['error'] = last_error
                            url_record['error_type'] = 'timeout'

                    except Exception as e:
                        error_msg = str(e).lower()
                        if 'blocked' in error_msg or '403' in error_msg or 'forbidden' in error_msg:
                            last_error = f"Blocked: {str(e)}"
                            url_record['error_type'] = 'blocked'
                            print(f"  ✗ Blocked by website - skipping")
                            url_record['error'] = last_error
                            break
                        elif 'network' in error_msg:
                            last_error = f"Network error: {str(e)}"
                            retry_count += 1
                            if retry_count >= max_retries:
                                print(f"  ✗ Failed after {max_retries} retries - Network error")
                                url_record['error'] = last_error
                                url_record['error_type'] = 'network'
                        else:
                            last_error = f"Extraction error: {str(e)}"
                            retry_count += 1
                            if retry_count >= max_retries:
                                print(f"  ✗ Failed: {str(e)}")
                                url_record['error'] = last_error
                                url_record['error_type'] = 'extraction'

                # Add human-like variable delay between products
                base_delay = random.uniform(2, 5)
                # Occasional longer pauses (like human taking a break)
                if random.random() < 0.1:  # 10% chance
                    base_delay += random.uniform(5, 15)
                    print(f"  ☕ Taking a longer break ({base_delay:.1f}s)...")
                await asyncio.sleep(base_delay)

            await browser.close()

        print(f"\n{'='*60}")
        print(f"✅ Scraping Complete!")
        print(f"   Total products scraped: {len(self.products)}")
        print(f"{'='*60}")

        return self.products

    def save_products(self, temp=False):
        """
        Save products to JSON file.

        Args:
            temp: If True, save to temporary file

        Returns:
            Path: Path to saved file
        """
        suffix = "_temp" if temp else ""
        output_path = self.data_dir / f"tj_products_full{suffix}.json"

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.products, f, indent=2, ensure_ascii=False)

        return output_path

    def update_tracking(self, url_records):
        """
        Update URL tracking file with current scraping status.

        Args:
            url_records: List of URL records with updated status
        """
        with open(self.urls_file, 'w', encoding='utf-8') as f:
            json.dump(url_records, f, indent=2)

    def print_summary(self):
        """Print summary statistics of scraped data."""
        if not self.products:
            print("No products scraped.")
            return

        print(f"\n{'='*60}")
        print("📊 SCRAPING SUMMARY")
        print(f"{'='*60}")
        print(f"Total products: {len(self.products)}")

        # Data completeness
        with_ingredients = sum(1 for p in self.products if p.get('ingredients'))
        with_nutrition = sum(1 for p in self.products if p.get('nutrition'))
        with_allergens_contains = sum(1 for p in self.products if len(p.get('allergens_contains', [])) > 0)
        with_allergens_may_contain = sum(1 for p in self.products if len(p.get('allergens_may_contain', [])) > 0)
        with_tags = sum(1 for p in self.products if len(p.get('tags', [])) > 0)

        print(f"\nData Completeness:")
        print(f"  Ingredients:         {with_ingredients}/{len(self.products)} ({with_ingredients/len(self.products)*100:.1f}%)")
        print(f"  Nutrition:           {with_nutrition}/{len(self.products)} ({with_nutrition/len(self.products)*100:.1f}%)")
        print(f"  Allergens (CONTAINS): {with_allergens_contains}/{len(self.products)} ({with_allergens_contains/len(self.products)*100:.1f}%)")
        print(f"  Allergens (MAY CONTAIN): {with_allergens_may_contain}/{len(self.products)} ({with_allergens_may_contain/len(self.products)*100:.1f}%)")
        print(f"  Tags:                {with_tags}/{len(self.products)} ({with_tags/len(self.products)*100:.1f}%)")

        # Category breakdown
        categories = {}
        prices = []
        for p in self.products:
            cat = p.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
            prices.append(p.get('price', 0))

        print(f"\nTop Categories:")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:10]:
            print(f"  {cat}: {count}")

        if prices:
            print(f"\nPrice Range:")
            print(f"  Min: ${min(prices):.2f}")
            print(f"  Max: ${max(prices):.2f}")
            print(f"  Avg: ${sum(prices)/len(prices):.2f}")

    async def run(self, limit=None, resume=False):
        """
        Main execution flow: scrape products and save to file.

        Args:
            limit: Optional limit on number of products (for testing)
            resume: If True, skip already-scraped URLs

        Returns:
            Path: Path to saved products file
        """
        print("""
╔══════════════════════════════════════════════════════════╗
║    Trader Joe's Product Details Scraper (Module 2)     ║
╚══════════════════════════════════════════════════════════╝
""")

        # Scrape products
        products = await self.scrape_all(limit=limit, resume=resume)

        # Save final results
        output_path = self.save_products()

        # Update tracking file with final status
        url_records, _ = self.load_urls(resume=False)
        self.update_tracking(url_records)

        # Print summary
        self.print_summary()

        print(f"\n✅ Module 2 complete!")
        print(f"   Output: {output_path}")
        print(f"\n📝 Next steps:")
        print(f"   1. Run scripts/create_embeddings_enhanced.py to create ChromaDB")
        print(f"   2. Test the app with updated data")
        print(f"{'='*60}\n")

        return output_path


async def main():
    """Main entry point"""
    import sys

    # Parse command line arguments
    test_mode = "--test" in sys.argv
    resume_mode = "--resume" in sys.argv
    headless = "--headless" in sys.argv

    scraper = ProductDetailsScraper(headless=headless)

    if test_mode:
        print("🧪 TEST MODE: Scraping 10 products")
        await scraper.run(limit=10, resume=resume_mode)
    else:
        print("🏃 FULL MODE: Scraping all products")
        await scraper.run(resume=resume_mode)


if __name__ == "__main__":
    print("""
Usage:
  python scrape_product_details.py            # Scrape all products (fresh start)
  python scrape_product_details.py --resume   # Resume from last scrape
  python scrape_product_details.py --test     # Test with 10 products
  python scrape_product_details.py --headless # Run without browser window

Features:
  • Auto-archives existing tj_products_full.json before overwriting
  • Scrapes: name, price, description, ingredients, nutrition, allergens, tags
  • Retry logic with exponential backoff (3 attempts)
  • Progress saving every 50 products
  • Human-like delays to avoid blocking
  • Resume capability to continue failed scrapes

Expected:
  • ~1,573 products to scrape
  • Time: ~15-30 minutes for full scrape
  • Note: Fresh food won't have ingredients
  • Note: Nutrition available only for Food & Beverages
""")

    asyncio.run(main())
