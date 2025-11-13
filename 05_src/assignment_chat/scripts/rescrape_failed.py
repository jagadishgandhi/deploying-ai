"""
Re-scrape products that previously failed to scrape
Targets the ~1009 products with "Unknown" names using the improved scraper
"""

import asyncio
import json
from pathlib import Path
import sys

# Add parent directory to path to import the scraper
sys.path.append(str(Path(__file__).parent.parent))
from scripts.scraper_two_step import TwoStepScraper


async def rescrape_failed_products():
    """Re-scrape products with Unknown names using improved scraper."""

    print("="*60)
    print("🔄 RE-SCRAPING FAILED PRODUCTS")
    print("="*60)

    # Load current products
    products_file = Path(__file__).parent.parent / "data" / "tj_products_full.json"

    if not products_file.exists():
        print(f"❌ Products file not found at {products_file}")
        print("   Run the initial scraper first!")
        return

    with open(products_file) as f:
        products = json.load(f)

    # Find failed products
    failed_products = [p for p in products if p.get('name') == 'Unknown']
    successful_products = [p for p in products if p.get('name') != 'Unknown']

    print(f"\n📊 Current Status:")
    print(f"   Total products: {len(products)}")
    print(f"   ✅ Successful: {len(successful_products)}")
    print(f"   ❌ Failed (Unknown): {len(failed_products)}")
    print(f"   Success rate: {len(successful_products)/len(products)*100:.1f}%")

    if not failed_products:
        print("\n✨ No failed products to re-scrape! All products have valid names.")
        return

    # Load URL tracking file
    tracking_file = Path(__file__).parent.parent / "data" / "product_urls.json"

    if not tracking_file.exists():
        print(f"❌ URL tracking file not found at {tracking_file}")
        print("   Cannot identify URLs for failed products.")
        return

    with open(tracking_file) as f:
        url_records = json.load(f)

    # Get IDs of failed products
    failed_ids = {p['id'] for p in failed_products}

    # Find URLs for failed products
    urls_to_rescrape = []
    for record in url_records:
        if record.get('product_id') in failed_ids:
            # Mark for re-scraping
            record['scraped'] = False
            record['error'] = 'Unknown name - needs re-scrape'
            urls_to_rescrape.append(record)

    print(f"\n🔍 Found {len(urls_to_rescrape)} URLs to re-scrape")

    if not urls_to_rescrape:
        print("⚠️  No matching URLs found for failed products")
        return

    # Save updated tracking file
    with open(tracking_file, 'w') as f:
        json.dump(url_records, f, indent=2)

    print(f"\n📝 Updated tracking file with {len(urls_to_rescrape)} products marked for re-scraping")

    # Initialize improved scraper
    print("\n🚀 Starting improved scraper with:")
    print("   • Network idle wait strategy")
    print("   • 30s timeout (increased from 20s)")
    print("   • 3 retry attempts with exponential backoff")
    print("   • Better error classification")
    print("   • Human-like delays")

    scraper = TwoStepScraper()

    # Load existing successful products
    scraper.products = successful_products

    print(f"\n📦 Loaded {len(scraper.products)} successful products")
    print("🔄 Starting re-scrape of failed products...")
    print("-"*60)

    # Run step 2 with resume=True to use the updated tracking
    await scraper.step2_scrape_details(resume=True)

    # Save final results
    output_file = scraper.save_products()

    # Load and analyze results
    with open(output_file) as f:
        final_products = json.load(f)

    new_failed = [p for p in final_products if p.get('name') == 'Unknown']
    new_successful = [p for p in final_products if p.get('name') != 'Unknown']

    print("\n" + "="*60)
    print("📊 RE-SCRAPE RESULTS")
    print("="*60)
    print(f"   Total products: {len(final_products)}")
    print(f"   ✅ Successful: {len(new_successful)}")
    print(f"   ❌ Still failed: {len(new_failed)}")
    print(f"   Success rate: {len(new_successful)/len(final_products)*100:.1f}%")

    # Calculate improvement
    previous_success = len(successful_products)
    current_success = len(new_successful)
    recovered = current_success - previous_success

    print(f"\n📈 Improvement:")
    print(f"   Previous successful: {previous_success}")
    print(f"   Current successful: {current_success}")
    print(f"   🎉 Recovered: {recovered} products")

    if recovered > 0:
        recovery_rate = recovered / len(failed_products) * 100
        print(f"   Recovery rate: {recovery_rate:.1f}%")

    # Show some recovered products
    if recovered > 0:
        print(f"\n🆕 Sample of recovered products:")
        recovered_products = [p for p in final_products
                             if p['id'] in failed_ids and p['name'] != 'Unknown'][:5]
        for p in recovered_products:
            print(f"   • {p['name']} - ${p.get('price', 0):.2f}")
            if p.get('ingredients'):
                print(f"     ✓ Has ingredients")
            if p.get('nutrition'):
                print(f"     ✓ Has nutrition")

    # Analyze remaining failures
    if new_failed:
        print(f"\n⚠️  {len(new_failed)} products still failing. Error analysis:")
        error_types = {}
        for record in url_records:
            if record.get('product_id') in {p['id'] for p in new_failed}:
                error_type = record.get('error_type', 'unknown')
                error_types[error_type] = error_types.get(error_type, 0) + 1

        for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {error_type}: {count} products")

    print("\n✅ Re-scraping complete!")
    print(f"   Output saved to: {output_file}")


async def main():
    """Main entry point"""
    await rescrape_failed_products()


if __name__ == "__main__":
    asyncio.run(main())