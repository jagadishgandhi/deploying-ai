"""
Service 3: Recipe Generator with Function Calling
Uses OpenAI function calling to generate recipes using Trader Joe's products
"""

from openai import OpenAI
import os
import json
from typing import List, Dict, Optional
from .product_search_service import ProductSearchService


class RecipeService:
    """
    Service for recipe generation with function calling.

    This service fulfills Assignment Requirement #3: Function Calling
    - Uses OpenAI function calling for tool orchestration
    - Searches products for recipe ingredients
    - Calculates recipe costs
    - Provides cooking instructions
    """

    def __init__(self, product_search: ProductSearchService = None):
        """
        Initialize Recipe Service.

        Args:
            product_search: ProductSearchService instance (created if not provided)
        """
        api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.product_search = product_search or ProductSearchService()

        # Define available tools/functions
        self.tools = self._define_tools()

    def _define_tools(self) -> List[Dict]:
        """
        Define OpenAI function calling tools.

        These tools allow the LLM to:
        1. Search for products matching recipe ingredients
        2. Calculate total cost of a recipe
        3. Get nutritional information for products
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_products_for_recipe",
                    "description": "Search Trader Joe's products that match recipe ingredients. Use this to find specific products needed for a recipe.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ingredients": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of ingredient names to search for (e.g., ['chicken', 'rice', 'vegetables'])"
                            },
                            "max_price_per_item": {
                                "type": "number",
                                "description": "Optional maximum price per item"
                            }
                        },
                        "required": ["ingredients"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_recipe_cost",
                    "description": "Calculate the total cost of recipe ingredients from Trader Joe's product IDs",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of product IDs to include in cost calculation"
                            }
                        },
                        "required": ["product_ids"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_product_details",
                    "description": "Get detailed information about a specific product by ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_id": {
                                "type": "string",
                                "description": "The product ID"
                            }
                        },
                        "required": ["product_id"]
                    }
                }
            }
        ]

    def generate_recipe(self, user_request: str) -> str:
        """
        Generate a recipe based on user request using function calling.

        Args:
            user_request: User's recipe request (e.g., "I want to make fried rice")

        Returns:
            Recipe with Uncle Joe's personality and product recommendations
        """
        # Check if client is available
        if not self.client:
            return "Haiyaa, Uncle Joe cannot make recipe now - need OpenAI API key! Please set OPENAI_API_KEY environment variable."

        # System message with Uncle Joe personality
        system_message = """You are Uncle Joe, helping create recipes using Trader Joe's products.

You have access to tools to:
1. Search for products at Trader Joe's
2. Calculate recipe costs
3. Get product details

When user asks for a recipe:
1. Use search_products_for_recipe to find needed ingredients
2. Use calculate_recipe_cost to get total cost
3. Provide recipe instructions in Uncle Joe's voice

Uncle Joe style:
- Drop articles ("This is rice" → "This rice")
- Simplified grammar ("It comes with" → "It come with")
- Use "Haiyaa" (disappointment), "Fuiyoh" (impressed), "Aiyaa" (concern)
- Passionate about quality ingredients
- Gives cooking tips
- Direct and honest

Provide:
- Ingredient list with Trader Joe's products
- Step-by-step cooking instructions
- Uncle Joe's tips and commentary
- Total cost and servings"""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_request}
        ]

        try:
            # Initial API call with function calling
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )

            # Process response and handle tool calls
            return self._process_response(response, messages)

        except Exception as e:
            print(f"Error generating recipe: {e}")
            return f"Aiyaa, Uncle Joe have problem making recipe for you. Error: {e}"

    def _process_response(self, response, messages: List[Dict]) -> str:
        """
        Process API response and handle tool calls recursively.

        Args:
            response: OpenAI API response
            messages: Conversation messages

        Returns:
            Final recipe text
        """
        response_message = response.choices[0].message

        # Check if there are tool calls
        if response_message.tool_calls:
            # Add assistant's response to messages
            messages.append(response_message)

            # Execute each tool call
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                print(f"🔧 Calling tool: {function_name} with args: {function_args}")

                # Execute the function
                function_response = self._execute_function(function_name, function_args)

                # Add function result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": json.dumps(function_response)
                })

            # Get final response after tool execution
            final_response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )

            return final_response.choices[0].message.content

        else:
            # No tool calls, return content directly
            return response_message.content

    def _execute_function(self, function_name: str, arguments: Dict) -> Dict:
        """
        Execute a function based on its name.

        Args:
            function_name: Name of the function to execute
            arguments: Function arguments

        Returns:
            Function result as dictionary
        """
        if function_name == "search_products_for_recipe":
            return self.search_products_for_recipe(
                ingredients=arguments['ingredients'],
                max_price_per_item=arguments.get('max_price_per_item')
            )

        elif function_name == "calculate_recipe_cost":
            return self.calculate_recipe_cost(
                product_ids=arguments['product_ids']
            )

        elif function_name == "get_product_details":
            return self.get_product_details(
                product_id=arguments['product_id']
            )

        else:
            return {"error": f"Unknown function: {function_name}"}

    def search_products_for_recipe(
        self,
        ingredients: List[str],
        max_price_per_item: Optional[float] = None
    ) -> Dict:
        """
        Search for products matching recipe ingredients.

        Args:
            ingredients: List of ingredient names
            max_price_per_item: Optional max price filter

        Returns:
            Dictionary with found products for each ingredient
        """
        results = {}

        for ingredient in ingredients:
            # Build filters
            filters = {}
            if max_price_per_item:
                filters['max_price'] = max_price_per_item

            # Search for this ingredient
            products = self.product_search.search(
                query=ingredient,
                filters=filters,
                limit=2  # Get top 2 matches per ingredient
            )

            results[ingredient] = [
                {
                    'id': p['id'],
                    'name': p['name'],
                    'price': p['price'],
                    'category': p['category']
                }
                for p in products
            ]

        return results

    def calculate_recipe_cost(self, product_ids: List[str]) -> Dict:
        """
        Calculate total cost of recipe from product IDs.

        Args:
            product_ids: List of product IDs

        Returns:
            Cost breakdown dictionary
        """
        total_cost = 0.0
        products = []

        for product_id in product_ids:
            product = self.product_search.get_product_by_id(product_id)

            if product:
                total_cost += product['price']
                products.append({
                    'id': product_id,
                    'name': product['name'],
                    'price': product['price']
                })
            else:
                print(f"Warning: Product {product_id} not found")

        return {
            'total_cost': round(total_cost, 2),
            'cost_per_serving': round(total_cost / 4, 2),  # Assume 4 servings
            'num_servings': 4,
            'products': products
        }

    def get_product_details(self, product_id: str) -> Dict:
        """
        Get detailed product information.

        Args:
            product_id: Product ID

        Returns:
            Product details dictionary
        """
        product = self.product_search.get_product_by_id(product_id)

        if product:
            return {
                'found': True,
                'product': product
            }
        else:
            return {
                'found': False,
                'error': f'Product {product_id} not found'
            }


# Example usage and testing
if __name__ == "__main__":
    print("Testing Recipe Service with Function Calling\n" + "="*60)

    service = RecipeService()

    # Test recipe requests
    test_requests = [
        "I want to make fried rice. What do I need from Trader Joe's?",
        "Give me a simple pasta recipe using what's available",
        "I need a quick breakfast idea under $10 total",
    ]

    for request in test_requests:
        print(f"\nUser Request: {request}")
        print("-" * 60)

        recipe = service.generate_recipe(request)

        print(recipe)
        print()
