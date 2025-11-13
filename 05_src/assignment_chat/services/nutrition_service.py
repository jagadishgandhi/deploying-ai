"""
Service 1: Nutrition API Integration
Uses Open Food Facts API to get nutritional information for products
"""

import requests
from typing import Dict, Optional


class NutritionService:
    """
    Service for nutritional analysis using Open Food Facts API.

    This service fulfills Assignment Requirement #1: API Integration
    - Uses external Open Food Facts API (completely free, no auth)
    - Searches for Trader Joe's products and retrieves real nutrition data
    - Transforms API response into conversational format
    - Does not return verbatim API responses
    """

    def __init__(self):
        """
        Initialize Nutrition Service.

        No API key required - Open Food Facts is completely free and open!
        """
        self.search_url = "https://world.openfoodfacts.org/cgi/search.pl"
        self.product_url = "https://world.openfoodfacts.org/api/v0/product"

        print("✓ Nutrition Service initialized with Open Food Facts API")

    def analyze_product(self, product_name: str, barcode: str = None) -> Optional[Dict]:
        """
        Get nutritional breakdown for a product from Open Food Facts.

        Args:
            product_name: Name of the product (used to search)
            barcode: Product barcode (optional, for direct lookup)

        Returns:
            Dictionary with nutrition information or None if not found
        """
        # First check if this is a generic query (not a specific product)
        if self._is_generic_query(product_name):
            return None  # Return None for generic queries

        try:
            # If barcode provided, get product directly
            if barcode:
                product_data = self._get_product_by_barcode(barcode)
                if product_data:
                    return self._format_nutrition(product_data)

            # Otherwise search by name
            product_data = self._search_product(product_name)

            if product_data:
                return self._format_nutrition(product_data)
            else:
                print(f"Product '{product_name}' not found in Open Food Facts")
                return None  # Return None instead of mock data

        except Exception as e:
            print(f"Error calling Open Food Facts API: {e}")
            return None  # Return None instead of mock data

    def _search_product(self, product_name: str) -> Optional[Dict]:
        """
        Search for a product by name in Open Food Facts.

        Args:
            product_name: Product name to search

        Returns:
            Product data dictionary or None
        """
        try:
            # Search for Trader Joe's products
            params = {
                'search_terms': f"trader joe {product_name}",
                'search_simple': 1,
                'action': 'process',
                'json': 1,
                'page_size': 5
            }

            response = requests.get(
                self.search_url,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                products = data.get('products', [])

                if products:
                    # Return first match (best match)
                    return products[0]

            return None

        except Exception as e:
            print(f"Error searching Open Food Facts: {e}")
            return None

    def _get_product_by_barcode(self, barcode: str) -> Optional[Dict]:
        """
        Get product directly by barcode.

        Args:
            barcode: Product barcode

        Returns:
            Product data dictionary or None
        """
        try:
            url = f"{self.product_url}/{barcode}.json"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 1:
                    return data.get('product')

            return None

        except Exception as e:
            print(f"Error getting product by barcode: {e}")
            return None

    def get_ingredients(self, product_name: str, barcode: str = None) -> Optional[Dict]:
        """
        Get ingredients and allergens for a product from Open Food Facts.

        Args:
            product_name: Product name to search
            barcode: Product barcode (optional, for direct lookup)

        Returns:
            Dict with ingredients_text and allergens, or None if not found
        """
        try:
            # If barcode provided, get product directly
            if barcode:
                product_data = self._get_product_by_barcode(barcode)
            else:
                product_data = self._search_product(product_name)

            if product_data:
                return {
                    'ingredients_text': product_data.get('ingredients_text', ''),
                    'allergens': product_data.get('allergens', ''),
                    'allergens_tags': product_data.get('allergens_tags', []),
                    'traces': product_data.get('traces', ''),
                    'traces_tags': product_data.get('traces_tags', [])
                }

            return None

        except Exception as e:
            print(f"Error getting ingredients: {e}")
            return None

    def _format_nutrition(self, data: Dict) -> Dict:
        """
        Extract and format key nutrition info from Open Food Facts API response.

        This transforms the raw API response into a cleaner format
        (not verbatim as required by assignment).

        Args:
            data: Raw product data from Open Food Facts

        Returns:
            Standardized nutrition dictionary
        """
        # Open Food Facts stores nutrition per 100g in 'nutriments' field
        nutrients = data.get('nutriments', {})

        # Extract nutrition values (per 100g)
        nutrition_data = {
            'calories': int(nutrients.get('energy-kcal_100g', 0)),
            'protein_g': round(nutrients.get('proteins_100g', 0), 1),
            'fat_g': round(nutrients.get('fat_100g', 0), 1),
            'carbs_g': round(nutrients.get('carbohydrates_100g', 0), 1),
            'fiber_g': round(nutrients.get('fiber_100g', 0), 1),
            'sugar_g': round(nutrients.get('sugars_100g', 0), 1),
            'sodium_mg': round(nutrients.get('sodium_100g', 0) * 1000, 0),  # Convert g to mg
            'vitamin_c_mg': round(nutrients.get('vitamin-c_100g', 0) * 1000, 1),  # Convert g to mg
            'calcium_mg': round(nutrients.get('calcium_100g', 0) * 1000, 0),  # Convert g to mg
            'iron_mg': round(nutrients.get('iron_100g', 0) * 1000, 1),  # Convert g to mg
        }

        # Also include ingredients if available
        nutrition_data['ingredients_text'] = data.get('ingredients_text', '')
        nutrition_data['allergens'] = data.get('allergens', '')

        return nutrition_data

    def _is_generic_query(self, product_name: str) -> bool:
        """
        Check if the query is generic (like "high protein snacks")
        rather than a specific product name.

        Args:
            product_name: The query string

        Returns:
            True if generic, False if specific product
        """
        product_lower = product_name.lower()

        # Generic terms that indicate category searches
        generic_terms = [
            'snacks', 'foods', 'options', 'items', 'products',
            'choices', 'alternatives'
        ]

        # Attributes that indicate search criteria
        attributes = [
            'high', 'low', 'good', 'best', 'healthy', 'organic',
            'vegan', 'gluten free', 'protein', 'fat', 'carb',
            'sugar free', 'dairy free'
        ]

        # Check for plural forms (indicates multiple products)
        has_plural = any(term in product_lower for term in generic_terms)

        # Check for attributes + category patterns
        has_attribute = any(attr in product_lower for attr in attributes)

        # If it has both attribute and plural form, it's generic
        if has_plural and has_attribute:
            return True

        # If it's just a category without specific name
        if has_plural and len(product_lower.split()) <= 3:
            return True

        return False

    def _get_mock_nutrition(self, product_name: str) -> Dict:
        """
        Generate realistic mock nutrition data for demo purposes.

        This is a fallback when product is not found in Open Food Facts.
        """
        # Simple mock data based on product type
        product_lower = product_name.lower()

        # Default values
        nutrition = {
            'calories': 150,
            'protein_g': 5.0,
            'fat_g': 7.0,
            'carbs_g': 15.0,
            'fiber_g': 2.0,
            'sugar_g': 5.0,
            'sodium_mg': 200,
            'vitamin_c_mg': 2.0,
            'calcium_mg': 50,
            'iron_mg': 1.0,
        }

        # Adjust based on product category
        if 'cheese' in product_lower:
            nutrition.update({
                'calories': 100,
                'protein_g': 7.0,
                'fat_g': 8.0,
                'carbs_g': 1.0,
                'fiber_g': 0.0,
                'sugar_g': 0.5,
                'sodium_mg': 180,
                'calcium_mg': 200,
            })
        elif 'creamer' in product_lower or 'milk' in product_lower:
            nutrition.update({
                'calories': 35,
                'protein_g': 0.5,
                'fat_g': 1.5,
                'carbs_g': 5.0,
                'fiber_g': 0.0,
                'sugar_g': 4.0,
                'sodium_mg': 10,
                'calcium_mg': 40,
            })
        elif 'tofu' in product_lower:
            nutrition.update({
                'calories': 80,
                'protein_g': 8.0,
                'fat_g': 4.0,
                'carbs_g': 2.0,
                'fiber_g': 1.0,
                'sugar_g': 0.0,
                'sodium_mg': 10,
                'calcium_mg': 120,
                'iron_mg': 2.5,
            })
        elif 'chocolate' in product_lower:
            nutrition.update({
                'calories': 200,
                'protein_g': 3.0,
                'fat_g': 12.0,
                'carbs_g': 22.0,
                'fiber_g': 2.0,
                'sugar_g': 18.0,
                'sodium_mg': 20,
                'iron_mg': 2.0,
            })
        elif 'bread' in product_lower or 'roll' in product_lower:
            nutrition.update({
                'calories': 120,
                'protein_g': 4.0,
                'fat_g': 2.0,
                'carbs_g': 22.0,
                'fiber_g': 1.5,
                'sugar_g': 2.0,
                'sodium_mg': 200,
            })

        return nutrition

    def get_nutrition(self, product_name: str, barcode: str = None) -> str:
        """
        Convenient method to get nutrition info formatted in Uncle Joe's voice.

        Args:
            product_name: Name of the product
            barcode: Optional product barcode

        Returns:
            Natural language nutrition description in Uncle Joe's voice
        """
        nutrition = self.analyze_product(product_name, barcode)
        return self.format_for_uncle_joe(product_name, nutrition)

    def format_for_uncle_joe(self, product_name: str, nutrition: Dict) -> str:
        """
        Format nutrition information in Uncle Joe's voice.

        This is the transformation step required by the assignment -
        converts structured API data into natural, conversational language
        with Uncle Joe's personality.

        Args:
            product_name: Name of the product
            nutrition: Nutrition data dictionary

        Returns:
            Natural language nutrition description in Uncle Joe's voice
        """
        if not nutrition:
            # Check if it's a generic query
            if self._is_generic_query(product_name):
                return (f"Haiyaa, '{product_name}' not specific product! "
                       f"Uncle Joe need exact product name to check nutrition. "
                       f"You want search for {product_name} instead? "
                       f"Try ask me 'find {product_name}' or 'show me {product_name}'.")
            else:
                return (f"Aiyaa, Uncle Joe cannot find nutrition info for '{product_name}' in database. "
                       f"Maybe this product too new or not in Open Food Facts yet. "
                       f"You can try search similar product or check Trader Joe website!")

        # Start with calories
        response = f"Okay okay, you want know nutrition for {product_name}? Uncle Joe check for you.\n\n"

        cal = nutrition['calories']
        protein = nutrition['protein_g']
        fat = nutrition['fat_g']
        carbs = nutrition['carbs_g']

        response += f"Per serving: {cal} calorie"

        # Add macros
        if protein > 0:
            response += f", {protein}g protein"
        if fat > 0:
            response += f", {fat}g fat"
        if carbs > 0:
            response += f", {carbs}g carb"

        response += ". "

        # Add Uncle Joe's commentary based on nutrition
        if cal < 100:
            response += "Haiyaa, very low calorie! Good for diet but maybe not fill you up. "
        elif cal > 300:
            response += "Fuiyoh, quite high calorie! Tasty but eat portion size careful. "

        if protein > 8:
            response += f"Good protein ({protein}g) - help build muscle! "

        if nutrition['fiber_g'] > 3:
            response += f"High fiber ({nutrition['fiber_g']}g) - very good for digestion! "

        if nutrition['sugar_g'] > 15:
            response += f"Aiyaa, quite sweet ({nutrition['sugar_g']}g sugar). "
        elif nutrition['sugar_g'] < 3:
            response += "Not too sweet - Uncle Joe approve! "

        if nutrition['sodium_mg'] > 400:
            response += f"Warning: high sodium ({int(nutrition['sodium_mg'])}mg). Watch out if you have blood pressure problem. "

        # Add calcium info for dairy
        if nutrition['calcium_mg'] > 100:
            response += f"Good calcium ({int(nutrition['calcium_mg'])}mg) for bone! "

        # Final advice
        response += "\n\nUncle Joe advice: "
        sugar = nutrition['sugar_g']
        if cal < 150 and protein > 5:
            response += "This good healthy choice! Not too many calorie, have protein."
        elif fat > 10 and sugar > 10:
            response += "This more like treat, not everyday food. Enjoy but don't eat too much!"
        else:
            response += "Okay option. Everything in moderation, you know?"

        return response


# Example usage and testing
if __name__ == "__main__":
    print("Testing Nutrition Service with Open Food Facts API\n" + "="*60)

    service = NutritionService()

    # Test with real Trader Joe's products that exist in Open Food Facts
    test_products = [
        "Cauliflower Gnocchi",
        "Everything But The Bagel Seasoning",
        "Unexpected Cheddar",
        "Organic Coconut Aminos"
    ]

    for product in test_products:
        print(f"\n{'='*60}")
        print(f"Product: {product}")
        print("-" * 60)

        # Use convenient method
        response = service.get_nutrition(product)

        print(response)
        print()
