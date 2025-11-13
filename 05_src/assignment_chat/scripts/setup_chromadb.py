"""
Setup ChromaDB with persistent storage for Trader Joe's products
Uses pre-computed embeddings from OpenAI
"""

import json
import os
from pathlib import Path
import chromadb
from chromadb.config import Settings
from tqdm import tqdm


class ChromaDBSetup:
    """Setup and populate ChromaDB with product embeddings"""

    def __init__(self, db_path='chroma_db'):
        self.db_path = Path(__file__).parent.parent / db_path

        # Create persistent client
        print(f"Initializing ChromaDB at: {self.db_path}")
        self.client = chromadb.PersistentClient(
            path=str(self.db_path)
        )

        self.collection_name = "trader_joes_products"
        self.collection = None

    def load_products_with_embeddings(self, input_path='data/tj_products_with_embeddings.json'):
        """Load products with embeddings"""

        json_file = Path(__file__).parent.parent / input_path

        if not json_file.exists():
            raise FileNotFoundError(f"Embeddings file not found: {json_file}")

        with open(json_file, 'r', encoding='utf-8') as f:
            products = json.load(f)

        # Filter products that have embeddings
        products_with_emb = [p for p in products if 'embedding' in p]

        print(f"✓ Loaded {len(products_with_emb)}/{len(products)} products with embeddings")

        return products_with_emb

    def create_or_get_collection(self):
        """Create or get existing collection"""

        try:
            # Try to get existing collection
            self.collection = self.client.get_collection(
                name=self.collection_name
            )
            print(f"✓ Found existing collection: {self.collection_name}")
            print(f"  Current count: {self.collection.count()} items")

            # Ask to reset
            print("\nReset collection? This will delete all existing data. (y/n): ", end='')
            response = input().strip().lower()

            if response == 'y':
                self.client.delete_collection(name=self.collection_name)
                print("  Deleted existing collection")
                self.collection = None

        except Exception:
            print(f"No existing collection found")
            self.collection = None

        if self.collection is None:
            # Create new collection
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={
                    "hnsw:space": "cosine",  # Use cosine similarity
                    "description": "Trader Joe's product catalog for Uncle Joe assistant"
                }
            )
            print(f"✓ Created new collection: {self.collection_name}")

        return self.collection

    def populate_collection(self, products, batch_size=100):
        """Add products to ChromaDB collection"""

        print(f"\nPopulating collection with {len(products)} products...")
        print(f"Batch size: {batch_size}")

        # Process in batches
        for i in tqdm(range(0, len(products), batch_size), desc="Adding to ChromaDB"):
            batch = products[i:i+batch_size]

            # Prepare batch data
            ids = []
            embeddings = []
            documents = []
            metadatas = []

            for product in batch:
                ids.append(product['id'])
                embeddings.append(product['embedding'])
                documents.append(product.get('searchable_text', product['name']))

                # Metadata (must be simple types only)
                metadatas.append({
                    'name': product['name'],
                    'price': product['price'],
                    'category': product['category'],
                    'url': product.get('url', ''),
                })

            # Add to collection
            try:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
            except Exception as e:
                print(f"\nError adding batch {i//batch_size + 1}: {e}")
                continue

        print(f"\n✓ Added {self.collection.count()} products to collection")

    def test_search(self):
        """Test the search functionality"""

        print(f"\n{'='*60}")
        print("Testing Search Functionality")
        print(f"{'='*60}")

        test_queries = [
            "cheese",
            "plant-based food",
            "chocolate dessert",
            "healthy snacks"
        ]

        for query in test_queries:
            print(f"\nQuery: '{query}'")
            results = self.collection.query(
                query_texts=[query],
                n_results=3
            )

            print("  Results:")
            for i, (id, metadata, distance) in enumerate(zip(
                results['ids'][0],
                results['metadatas'][0],
                results['distances'][0]
            ), 1):
                print(f"    {i}. {metadata['name']} - ${metadata['price']} (similarity: {1-distance:.3f})")

    def print_stats(self):
        """Print database statistics"""

        print(f"\n{'='*60}")
        print("ChromaDB Statistics")
        print(f"{'='*60}")

        print(f"Database path: {self.db_path}")
        print(f"Collection name: {self.collection_name}")
        print(f"Total products: {self.collection.count()}")

        # Calculate database size
        if self.db_path.exists():
            total_size = sum(f.stat().st_size for f in self.db_path.rglob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)
            print(f"Database size: {size_mb:.2f} MB")

            if size_mb > 40:
                print(f"⚠️  WARNING: Database size exceeds 40MB limit!")


def main():
    """Main function"""

    print("="*60)
    print("ChromaDB Setup for Trader Joe's Products")
    print("="*60)

    # Initialize setup
    setup = ChromaDBSetup()

    # Load products with embeddings
    products = setup.load_products_with_embeddings()

    # Create/get collection
    collection = setup.create_or_get_collection()

    # Populate collection
    setup.populate_collection(products)

    # Test search
    setup.test_search()

    # Print stats
    setup.print_stats()

    print(f"\n{'='*60}")
    print("✅ ChromaDB setup complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
