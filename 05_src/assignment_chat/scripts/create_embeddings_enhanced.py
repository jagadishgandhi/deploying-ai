"""
Generate embeddings for scraped Trader Joe's products using OpenAI's API
Enhanced version that includes nutrition, ingredients, and tags in the embeddings
"""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from openai import OpenAI
from typing import List, Dict
import time


def create_product_text(product: Dict) -> str:
    """
    Create a comprehensive text representation of a product for embedding.
    Includes all relevant fields for better semantic search.
    """
    parts = []

    # Basic info
    parts.append(f"Product: {product.get('name', 'Unknown')}")
    parts.append(f"Category: {product.get('category', 'Food')}")

    if product.get('subcategory'):
        parts.append(f"Subcategory: {product['subcategory']}")

    # Price and unit
    parts.append(f"Price: ${product.get('price', 0):.2f}")
    if product.get('unit'):
        parts.append(f"Unit: {product['unit']}")

    # Description
    if product.get('description'):
        parts.append(f"Description: {product['description'][:500]}")  # Limit description length

    # Tags - very important for search
    if product.get('tags'):
        parts.append(f"Tags: {', '.join(product['tags'])}")

    # Ingredients - important for dietary restrictions
    if product.get('ingredients'):
        parts.append(f"Ingredients: {product['ingredients'][:300]}")  # First 300 chars

    # Allergens
    if product.get('allergens'):
        parts.append(f"Allergens: {', '.join(product['allergens'])}")

    # Nutrition highlights
    if product.get('nutrition'):
        nutrition = product['nutrition']
        nutrition_facts = []

        if 'calories' in nutrition:
            nutrition_facts.append(f"{nutrition['calories']} calories")
        if 'protein_g' in nutrition:
            nutrition_facts.append(f"{nutrition['protein_g']}g protein")
        if 'total_fat_g' in nutrition:
            nutrition_facts.append(f"{nutrition['total_fat_g']}g fat")
        if 'total_carbohydrate_g' in nutrition:
            nutrition_facts.append(f"{nutrition['total_carbohydrate_g']}g carbs")
        if 'dietary_fiber_g' in nutrition:
            nutrition_facts.append(f"{nutrition['dietary_fiber_g']}g fiber")

        if nutrition_facts:
            parts.append(f"Nutrition: {', '.join(nutrition_facts)}")

    # Special flags
    if product.get('limited_time'):
        parts.append("Limited Time Product")

    # Combine all parts
    return " | ".join(parts)


def generate_embeddings(products: List[Dict], api_key: str, batch_size: int = 50) -> List[Dict]:
    """
    Generate embeddings for products using OpenAI's text-embedding-3-small model.

    Args:
        products: List of product dictionaries
        api_key: OpenAI API key
        batch_size: Number of products to process at once

    Returns:
        List of products with embedding field added
    """
    client = OpenAI(api_key=api_key)
    products_with_embeddings = []

    print(f"Generating embeddings for {len(products)} products...")
    print("Using model: text-embedding-3-small")

    for i in range(0, len(products), batch_size):
        batch = products[i:i+batch_size]
        batch_texts = []

        # Create text representations for each product
        for product in batch:
            text = create_product_text(product)
            batch_texts.append(text)

        try:
            # Generate embeddings for the batch
            response = client.embeddings.create(
                input=batch_texts,
                model="text-embedding-3-small"
            )

            # Add embeddings to products
            for j, product in enumerate(batch):
                product_with_embedding = product.copy()
                product_with_embedding['embedding'] = response.data[j].embedding
                product_with_embedding['embedding_text'] = batch_texts[j]  # Store text used for embedding
                products_with_embeddings.append(product_with_embedding)

            print(f"  Processed {min(i+batch_size, len(products))}/{len(products)} products")

            # Small delay to avoid rate limits
            if i + batch_size < len(products):
                time.sleep(0.5)

        except Exception as e:
            print(f"Error generating embeddings for batch {i//batch_size + 1}: {e}")
            # Add products without embeddings
            for product in batch:
                products_with_embeddings.append(product)

    return products_with_embeddings


def archive_existing_file(output_file: Path) -> Path:
    """
    Archive existing embeddings file if it exists.
    Archives to: tj_products_with_embeddings_YYYYMMDD_HHMMSS.json

    Args:
        output_file: Path to the file to archive

    Returns:
        Path to archive file if created, None otherwise
    """
    if output_file.exists():
        # Get file size for display
        file_size_mb = output_file.stat().st_size / (1024 * 1024)

        # Generate timestamp for archive
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"tj_products_with_embeddings_{timestamp}.json"
        archive_path = output_file.parent / archive_name

        # Copy to archive
        shutil.copy2(output_file, archive_path)
        print(f"📦 Archived existing embeddings file ({file_size_mb:.1f} MB) to: {archive_name}")
        return archive_path
    return None


def main():
    """Main execution"""

    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not set!")
        print("Please set: export OPENAI_API_KEY='your-key-here'")
        return

    # Load products
    input_file = Path(__file__).parent.parent / "data" / "tj_products_full.json"

    if not input_file.exists():
        print(f"❌ Error: {input_file} not found!")
        print("Run the scraper first to collect products")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        products = json.load(f)

    print(f"📂 Loaded {len(products)} products from {input_file}")

    # Show data quality
    with_nutrition = len([p for p in products if p.get('nutrition')])
    with_ingredients = len([p for p in products if p.get('ingredients')])
    with_tags = len([p for p in products if p.get('tags')])

    print(f"\n📊 Data Quality:")
    print(f"  With nutrition: {with_nutrition} ({with_nutrition*100//len(products)}%)")
    print(f"  With ingredients: {with_ingredients} ({with_ingredients*100//len(products)}%)")
    print(f"  With tags: {with_tags} ({with_tags*100//len(products)}%)")

    # Define output file path
    output_file = Path(__file__).parent.parent / "data" / "tj_products_with_embeddings.json"

    # Archive existing embeddings file before generating new ones
    archive_existing_file(output_file)

    # Generate embeddings
    print(f"\n🚀 Starting embedding generation...")
    products_with_embeddings = generate_embeddings(products, api_key)

    # Save results
    print(f"\n💾 Saving embeddings to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(products_with_embeddings, f, indent=2, ensure_ascii=False)

    # Calculate file size
    file_size_mb = output_file.stat().st_size / (1024 * 1024)

    print(f"\n✅ Embeddings generated successfully!")
    print(f"   Output file: {output_file}")
    print(f"   File size: {file_size_mb:.1f} MB")
    print(f"   Products with embeddings: {len([p for p in products_with_embeddings if 'embedding' in p])}")

    # Show sample embedding text
    if products_with_embeddings and 'embedding_text' in products_with_embeddings[0]:
        print(f"\n📝 Sample embedding text:")
        print(f"   {products_with_embeddings[0]['embedding_text'][:200]}...")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║     Enhanced Embeddings Generator for TJ Products        ║
╚══════════════════════════════════════════════════════════╝

This script generates OpenAI embeddings for Trader Joe's products
including nutrition, ingredients, tags, and descriptions.

Requirements:
  - OPENAI_API_KEY environment variable
  - tj_products_full.json with scraped products

Features:
  • Auto-archives existing embeddings file before creating new one
  • Embeddings saved to: tj_products_with_embeddings.json
  • Archives saved as: tj_products_with_embeddings_YYYYMMDD_HHMMSS.json

Cost estimate: ~$0.02 per 1000 products with text-embedding-3-small
""")

    main()