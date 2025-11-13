"""
Service 2: Product Search with ChromaDB
Semantic search across Trader Joe's product catalog using vector embeddings
"""

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import json
import os
from pathlib import Path
from typing import List, Dict, Optional


class ProductSearchService:
    """
    Service for semantic product search using ChromaDB.

    This service fulfills Assignment Requirement #2: Semantic Query
    - Uses ChromaDB with persistent file storage (not Docker)
    - Performs semantic search using pre-computed OpenAI embeddings
    - Supports hybrid search (vector similarity + metadata filtering)
    - Dataset under 40MB
    """

    def __init__(self, db_path: str = None, products_file: str = None):
        """
        Initialize Product Search Service.

        Args:
            db_path: Path to ChromaDB directory (default: chroma_db)
            products_file: Path to products JSON file for metadata lookups
        """
        # Set paths relative to service file
        service_dir = Path(__file__).parent.parent

        if db_path is None:
            db_path = service_dir / "chroma_db"

        if products_file is None:
            # Try embeddings file first, then fall back to full products
            embeddings_file = service_dir / "data" / "tj_products_with_embeddings.json"
            full_file = service_dir / "data" / "tj_products_full.json"
            if embeddings_file.exists():
                products_file = embeddings_file
            elif full_file.exists():
                products_file = full_file
            else:
                products_file = embeddings_file  # Default fallback

        self.db_path = Path(db_path)
        self.products_file = Path(products_file)

        # Load products for detailed lookups
        self.products_map = self._load_products()

        # Initialize OpenAI embedding function for queries
        # IMPORTANT: Must use same model that was used to create the collection
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️  OPENAI_API_KEY not set. Using fallback search without embeddings.")
            self.embedding_function = None
            self.use_openai_embeddings = False
        else:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=api_key)
                self.use_openai_embeddings = True
                print("✓ Using OpenAI embeddings for search")
            except Exception as e:
                print(f"⚠️  Error initializing OpenAI client: {e}")
                self.embedding_function = None
                self.use_openai_embeddings = False

        # Initialize ChromaDB client
        try:
            self.client = chromadb.PersistentClient(path=str(self.db_path))
            self.collection = self.client.get_collection("trader_joes_products")
            print(f"✓ Connected to ChromaDB: {self.collection.count()} products")
        except Exception as e:
            print(f"⚠️  Error connecting to ChromaDB: {e}")
            print("   Run scripts/setup_chromadb.py first!")
            self.collection = None

    def _load_products(self) -> Dict:
        """Load products into a dictionary for quick lookup."""
        if not self.products_file.exists():
            print(f"⚠️  Products file not found: {self.products_file}")
            return {}

        with open(self.products_file, 'r') as f:
            products = json.load(f)

        # Create ID -> product mapping
        return {p['id']: p for p in products}

    def search(
        self,
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Search products with optional filters.

        Args:
            query: Search query (natural language)
            filters: Optional filters dict:
                - max_price: Maximum price
                - min_price: Minimum price
                - category: Product category
                - categories: List of categories
            limit: Number of results to return

        Returns:
            List of matching products with similarity scores
        """
        if not self.collection:
            return []

        # Build ChromaDB where filter
        where_filter = self._build_where_filter(filters)

        try:
            # Generate query embedding using OpenAI
            if self.use_openai_embeddings:
                # Generate embedding using OpenAI API directly
                response = self.openai_client.embeddings.create(
                    input=query,
                    model="text-embedding-3-small"
                )
                query_embedding = response.data[0].embedding

                # Query ChromaDB with pre-computed embedding
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    where=where_filter if where_filter else None
                )
            else:
                # Fallback: search by metadata when embeddings not available
                # This won't be as accurate but at least returns something
                print("⚠️  Falling back to metadata-based search")
                # Get all products and filter manually
                all_items = self.collection.get(limit=100)

                # Simple text matching on metadata
                matching_products = []
                query_lower = query.lower()

                for i, metadata in enumerate(all_items['metadatas']):
                    name = metadata.get('name', '').lower()
                    category = metadata.get('category', '').lower()
                    tags_str = metadata.get('tags', '[]')

                    # Check if query appears in name, category, or tags
                    if query_lower in name or query_lower in category or query_lower in tags_str:
                        matching_products.append({
                            'ids': [[all_items['ids'][i]]],
                            'metadatas': [[metadata]],
                            'distances': [[0.5]]  # Arbitrary distance for fallback
                        })

                if matching_products and len(matching_products) > 0:
                    # Format as ChromaDB results
                    results = {
                        'ids': [item['ids'][0] for item in matching_products[:limit]],
                        'metadatas': [item['metadatas'][0] for item in matching_products[:limit]],
                        'distances': [item['distances'][0] for item in matching_products[:limit]]
                    }
                    results = {
                        'ids': [results['ids']],
                        'metadatas': [results['metadatas']],
                        'distances': [results['distances']]
                    }
                else:
                    results = {'ids': [[]], 'metadatas': [[]], 'distances': [[]]}

            # Format results
            return self._format_results(results)

        except Exception as e:
            print(f"Error searching: {e}")
            return []

    def _build_where_filter(self, filters: Optional[Dict]) -> Optional[Dict]:
        """Build ChromaDB where filter from user filters."""
        if not filters:
            return None

        where = {}

        # Price filters
        if 'max_price' in filters:
            where['price'] = {'$lte': filters['max_price']}

        if 'min_price' in filters:
            if 'price' in where:
                where['price']['$gte'] = filters['min_price']
            else:
                where['price'] = {'$gte': filters['min_price']}

        # Category filter
        if 'category' in filters:
            where['category'] = filters['category']

        # Multiple categories
        if 'categories' in filters:
            where['category'] = {'$in': filters['categories']}

        return where if where else None

    def _format_results(self, results: Dict) -> List[Dict]:
        """
        Format ChromaDB query results into clean product dictionaries.

        Args:
            results: Raw ChromaDB query results

        Returns:
            List of formatted product dictionaries
        """
        products = []

        if not results['ids'] or not results['ids'][0]:
            return products

        for i in range(len(results['ids'][0])):
            product_id = results['ids'][0][i]
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]

            # Get full product details if available
            full_product = self.products_map.get(product_id, {})

            product = {
                'id': product_id,
                'name': metadata.get('name', full_product.get('name', 'Unknown')),
                'price': metadata.get('price', full_product.get('price', 0)),
                'category': metadata.get('category', full_product.get('category', 'Unknown')),
                'url': metadata.get('url', full_product.get('url', '')),
                'similarity': round(1 - distance, 3),  # Convert distance to similarity
                'distance': round(distance, 3)
            }

            products.append(product)

        return products

    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        """
        Get a specific product by ID.

        Args:
            product_id: Product ID

        Returns:
            Product dictionary or None
        """
        return self.products_map.get(product_id)

    def get_categories(self) -> List[str]:
        """
        Get list of all product categories.

        Returns:
            List of unique categories
        """
        categories = set()
        for product in self.products_map.values():
            if 'category' in product:
                categories.add(product['category'])

        return sorted(list(categories))

    def get_ingredients(self, product_name: str) -> Optional[Dict]:
        """
        Get ingredients for a product from our local database.

        This method searches for a product by name and returns its ingredients
        if available in our ChromaDB/JSON data.

        Args:
            product_name: Name of the product to get ingredients for

        Returns:
            Dictionary with ingredients data or None if not found:
            {
                'product_name': str,
                'ingredients': str,
                'allergens': list,
                'found': bool,
                'source': 'local'
            }
        """
        # First try to find the product using semantic search
        results = self.search(product_name, limit=1)

        if not results:
            return None

        # Get the best matching product
        best_match = results[0]
        product_id = best_match['id']

        # Get full product details from our products map
        full_product = self.products_map.get(product_id)

        if not full_product:
            return None

        # Extract ingredients information
        ingredients_data = {
            'product_name': full_product.get('name', 'Unknown'),
            'ingredients': None,
            'allergens': [],
            'found': False,
            'source': 'local'
        }

        # Check if we have ingredients in the product data
        if 'ingredients' in full_product and full_product['ingredients']:
            ingredients_data['ingredients'] = full_product['ingredients']
            ingredients_data['found'] = True

        # Check for allergens (may be in different fields)
        if 'allergens' in full_product:
            allergens = full_product['allergens']
            if isinstance(allergens, list):
                ingredients_data['allergens'] = allergens
            elif isinstance(allergens, str) and allergens:
                # Parse comma-separated allergens
                ingredients_data['allergens'] = [a.strip() for a in allergens.split(',')]

        # Also check for allergen warnings
        if 'allergen_info' in full_product and full_product['allergen_info']:
            if not ingredients_data['allergens']:
                ingredients_data['allergens'] = []
            ingredients_data['allergens'].append(full_product['allergen_info'])

        return ingredients_data

    def format_for_uncle_joe(self, query: str, results: List[Dict]) -> str:
        """
        Format search results in Uncle Joe's voice.

        Args:
            query: Original search query
            results: List of product results

        Returns:
            Natural language response in Uncle Joe's voice
        """
        if not results:
            return f"Aiyaa, Uncle Joe cannot find '{query}' at Trader Joe. Maybe you try different search? Or we don't have this item yet."

        # Opening
        response = f"Fuiyoh! Uncle Joe find {len(results)} item"
        if len(results) > 1:
            response += "s"
        response += " for you:\n\n"

        # List products
        for i, product in enumerate(results, 1):
            response += f"{i}. {product['name']} - ${product['price']:.2f}"

            # Add category
            response += f" ({product['category']})"

            # Add Uncle Joe's commentary for some items
            name_lower = product['name'].lower()
            price = product['price']

            if price < 3.0:
                response += " - Haiyaa, very cheap!"
            elif price > 10.0:
                response += " - Expensive but maybe worth it"

            if 'organic' in name_lower:
                response += " - Organic, very good quality"

            if 'cheese' in name_lower:
                response += " - Uncle Joe love cheese!"

            response += "\n"

        # Closing
        response += "\nWhich one you want know more about? Uncle Joe can tell you nutrition or give recipe idea!"

        return response


# Example usage and testing
if __name__ == "__main__":
    print("Testing Product Search Service\n" + "="*60)

    service = ProductSearchService()

    if not service.collection:
        print("\n⚠️  ChromaDB not set up. Run scripts/setup_chromadb.py first!")
        exit(1)

    # Test queries
    test_queries = [
        ("cheese", {}),
        ("plant-based food", {}),
        ("chocolate", {"max_price": 5.0}),
        ("healthy snacks", {}),
        ("breakfast", {"categories": ["Bakery", "Dairy"]}),
    ]

    for query, filters in test_queries:
        print(f"\nQuery: '{query}'")
        if filters:
            print(f"Filters: {filters}")
        print("-" * 60)

        results = service.search(query, filters=filters, limit=3)
        response = service.format_for_uncle_joe(query, results)

        print(response)

    # Show available categories
    print("\n" + "="*60)
    print("Available Categories:")
    for cat in service.get_categories():
        print(f"  - {cat}")
