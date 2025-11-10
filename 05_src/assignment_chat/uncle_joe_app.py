"""
Uncle Joe - Trader Joe's AI Shopping Assistant
Main Gradio chat interface integrating all three services
"""

import gradio as gr
from openai import OpenAI
import os
from typing import List, Tuple, Optional
from services.nutrition_service import NutritionService
from services.product_search_service import ProductSearchService
from services.recipe_service import RecipeService


class UncleJoeAssistant:
    """
    Main orchestrator for Uncle Joe assistant.

    Integrates all three services:
    - Service 1: Nutrition API (Open Food Facts)
    - Service 2: Product Search (ChromaDB + Vector Embeddings)
    - Service 3: Recipe Generator (OpenAI Function Calling)
    """

    def __init__(self):
        """Initialize all services and OpenAI client."""
        print("🔄 Initializing Uncle Joe Assistant...")

        # Initialize services
        self.nutrition_service = NutritionService()
        self.product_search = ProductSearchService()
        self.recipe_service = RecipeService(product_search=self.product_search)

        # Initialize OpenAI for conversation orchestration
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️  OPENAI_API_KEY not set. Using rule-based intent detection.")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)

        # System prompt for Uncle Joe personality
        self.system_prompt = """You are Uncle Joe, a helpful Trader Joe's shopping assistant based on Uncle Roger's personality.

Your personality:
- Drop articles: "This is rice" → "This rice"
- Simplified grammar: "It comes with" → "It come with"
- Signature phrases: "Haiyaa" (disappointment), "Fuiyoh" (impressed), "Aiyaa" (concern)
- Passionate about quality food and cooking
- Give practical cooking tips
- Direct and honest

You have access to:
1. Nutrition information for products (Open Food Facts API)
2. Product search across Trader Joe's catalog (semantic search)
3. Recipe generation using available products

Guidelines:
- Stay on topic: only discuss food, cooking, grocery shopping, nutrition
- Be helpful and friendly
- Refuse off-topic requests politely
- Never make up product availability - use search results only
- Provide practical cooking advice"""

        print("✅ Uncle Joe Assistant ready!")

    def detect_intent(self, message: str) -> str:
        """
        Detect user intent from message using LLM with fallback to rule-based.

        Args:
            message: User message

        Returns:
            Intent: 'nutrition', 'ingredients', 'search', 'recipe', 'chat', or 'off_topic'
        """
        message_lower = message.lower()

        # Fast path: Check for obvious off-topic keywords first
        off_topic_keywords = [
            'politics', 'election', 'vote', 'president',
            'weather', 'stock', 'crypto', 'investment',
            'math', 'calculate', 'equation', 'solve',
            'code', 'program', 'python', 'javascript'
        ]

        if any(keyword in message_lower for keyword in off_topic_keywords):
            return 'off_topic'

        # Try LLM-based intent detection if OpenAI client is available
        if self.client:
            try:
                return self._llm_detect_intent(message)
            except Exception as e:
                print(f"⚠️  LLM intent detection failed: {e}")
                # Fall through to rule-based detection

        # Fallback to improved rule-based detection
        return self._rule_based_detect_intent(message)

    def _llm_detect_intent(self, message: str) -> str:
        """
        Use LLM to accurately classify intent with few-shot examples.

        Args:
            message: User message

        Returns:
            Intent classification
        """
        prompt = """You are an intent classifier for Uncle Joe, a Trader Joe's grocery shopping assistant.

Classify the user's message into ONE of these intents:
- search: User wants to find/discover products (e.g., looking for items with certain attributes)
- nutrition: User wants specific nutrition information about a specific product
- ingredients: User wants to know the ingredients or allergen information for a specific product
- recipe: User wants cooking recipes or meal ideas
- chat: General conversation or greeting
- off_topic: Not related to food/grocery shopping

Important distinctions:
- "High protein snacks" → search (looking for products with an attribute)
- "What's the protein in cauliflower gnocchi?" → nutrition (asking about specific nutrient in specific product)
- "What are the ingredients in sriracha tofu?" → ingredients (asking about ingredients list)
- "Does this have gluten?" → ingredients (asking about allergen/ingredient presence)
- "Healthy options" → search (looking for products)
- "Is this healthy?" → nutrition (asking about nutritional quality)
- "Vegan cheese" → search (looking for products)
- "How many calories in the vegan cheese?" → nutrition (specific nutrient question)
- "What's in the vegan cheese?" → ingredients (asking what it contains)

Examples:
User: "High protein snacks"
Intent: search

User: "What's the protein content in Cauliflower Gnocchi?"
Intent: nutrition

User: "What are the ingredients in Sriracha Flavored Baked Tofu?"
Intent: ingredients

User: "Find me gluten free pasta"
Intent: search

User: "How many calories in Everything Bagel Seasoning?"
Intent: nutrition

User: "What's in the Everything Bagel Seasoning?"
Intent: ingredients

User: "Show me healthy snacks"
Intent: search

User: "I want to make fried rice"
Intent: recipe

User: "Low fat options"
Intent: search

User: "Does the tofu contain soy?"
Intent: ingredients

User: "Hello"
Intent: chat

User: "What's the weather?"
Intent: off_topic

Now classify this message:
User: "{message}"
Intent:"""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",  # Fast and cheap model for intent classification
            messages=[
                {"role": "system", "content": "You are a precise intent classifier. Respond with ONLY the intent label."},
                {"role": "user", "content": prompt.format(message=message)}
            ],
            temperature=0,  # Deterministic for consistency
            max_tokens=10
        )

        intent = response.choices[0].message.content.strip().lower()

        # Validate the intent
        valid_intents = ['nutrition', 'ingredients', 'search', 'recipe', 'chat', 'off_topic']
        if intent in valid_intents:
            return intent
        else:
            print(f"⚠️  Invalid intent from LLM: {intent}, falling back to rule-based")
            return self._rule_based_detect_intent(message)

    def _rule_based_detect_intent(self, message: str) -> str:
        """
        Improved rule-based intent detection as fallback.

        Args:
            message: User message

        Returns:
            Intent classification
        """
        message_lower = message.lower()

        # Ingredients patterns (check first to avoid confusion with nutrition)
        ingredients_patterns = [
            'ingredients', 'what are the ingredients', "what's in", 'what is in',
            'made from', 'made of', 'contains', 'contain', 'allergen',
            'gluten in', 'dairy in', 'soy in', 'nuts in', 'egg in'
        ]
        if any(pattern in message_lower for pattern in ingredients_patterns):
            return 'ingredients'

        # More specific nutrition patterns
        nutrition_patterns = [
            'nutrition', 'calories in', 'how many calories', 'how much protein',
            'how much fat', 'how much carb', 'protein in', 'fat in', 'carbs in',
            'vitamin', 'nutrient', 'nutrition facts', 'nutrition information'
        ]
        if any(pattern in message_lower for pattern in nutrition_patterns):
            return 'nutrition'

        # Recipe patterns
        recipe_keywords = ['recipe', 'cook', 'make', 'prepare', 'how to cook', 'how do i make', 'dish', 'meal']
        if any(keyword in message_lower for keyword in recipe_keywords):
            return 'recipe'

        # Search patterns - now including product attributes
        search_patterns = [
            'find', 'search', 'look for', 'do you have', 'where is', 'show me', 'recommend',
            'what products', 'which products', 'any products', 'products with',
            'snack', 'food', 'item', 'option', 'cheese', 'pasta', 'sauce'
        ]

        # Check for attribute + product patterns (e.g., "high protein snacks")
        attributes = ['high', 'low', 'good', 'best', 'healthy', 'organic', 'vegan', 'gluten free']
        product_categories = ['snack', 'food', 'product', 'item', 'option', 'cheese', 'pasta', 'bar']

        has_attribute = any(attr in message_lower for attr in attributes)
        has_category = any(cat in message_lower for cat in product_categories)

        if any(pattern in message_lower for pattern in search_patterns) or (has_attribute and has_category):
            return 'search'

        # Short phrases default to search (single products like "cheese", "wasabi")
        words = message_lower.strip('?.,! ').split()
        if len(words) <= 2 and not message_lower.startswith(('hi', 'hello', 'hey', 'bye', 'thank')):
            return 'search'

        # Default to chat
        return 'chat'

    def extract_product_name(self, message: str) -> Optional[str]:
        """
        Extract product name from user message.

        Simple heuristic-based extraction.
        In production, could use NER or LLM extraction.
        """
        message_lower = message.lower()

        # Remove common query phrases (extended list for ingredients)
        phrases_to_remove = [
            'what are the ingredients in',
            'what ingredients are in',
            "what's in the",
            "what's in",
            'what is in',
            'ingredients in',
            'ingredients for',
            'tell me the ingredients for',
            'does the', 'does this',
            'contain', 'have',
            'what allergens are in the',
            'what allergens are in',
            'allergens in',
            # Nutrition phrases
            'nutrition for', 'calories in',
            'how many calories', 'how much protein',
            'tell me about', 'what is',
            # Search phrases
            'find', 'search for', 'look for'
        ]

        for phrase in phrases_to_remove:
            if phrase in message_lower:
                message_lower = message_lower.replace(phrase, '')

        # Also remove question-related words at the end
        message_lower = message_lower.replace('contain gluten', '')
        message_lower = message_lower.replace('have gluten', '')
        message_lower = message_lower.replace('contain soy', '')
        message_lower = message_lower.replace('have dairy', '')

        # Clean up
        product_name = message_lower.strip('?.,! ')

        # Remove 'the' at the beginning if present
        if product_name.startswith('the '):
            product_name = product_name[4:]

        return product_name if product_name else None

    def handle_off_topic(self) -> str:
        """Handle off-topic requests with guardrails."""
        return ("Haiyaa, Uncle Joe only know about food and cooking! "
                "Ask me about Trader Joe product, nutrition, or recipe. "
                "For other thing, you need ask someone else lah.")

    def handle_nutrition(self, message: str) -> str:
        """
        Handle nutrition queries.

        Args:
            message: User message

        Returns:
            Nutrition information in Uncle Joe's voice
        """
        product_name = self.extract_product_name(message)

        if not product_name:
            return ("Uncle Joe need know which product you want check! "
                   "Tell me product name, like 'Cauliflower Gnocchi' or 'Unexpected Cheddar'.")

        # Get nutrition info
        return self.nutrition_service.get_nutrition(product_name)

    def handle_ingredients(self, message: str) -> str:
        """
        Handle ingredients queries.

        Args:
            message: User message

        Returns:
            Ingredients information in Uncle Joe's voice
        """
        # Extract product name from message
        product_name = self.extract_product_name(message)

        if not product_name:
            return ("Uncle Joe need know which product you want check ingredients! "
                   "Tell me product name, like 'Sriracha Flavored Baked Tofu' or 'Everything Bagel Seasoning'.")

        # First try to get from local database
        local_ingredients = self.product_search.get_ingredients(product_name)

        if local_ingredients and local_ingredients['found']:
            # Format response with local data
            response = f"Okay okay, you want know what inside {local_ingredients['product_name']}? Uncle Joe tell you:\n\n"
            response += f"**Ingredients:** {local_ingredients['ingredients']}\n"

            if local_ingredients['allergens']:
                response += f"\n**Allergen Warning:** {', '.join(local_ingredients['allergens'])}\n"
                response += "Haiyaa, be careful if you have allergy!\n"

            return response

        # Try Open Food Facts as fallback
        open_food_facts_data = self.nutrition_service.get_ingredients(product_name)

        if open_food_facts_data and open_food_facts_data.get('ingredients_text'):
            response = f"Uncle Joe find ingredients for {product_name} from Open Food Facts:\n\n"
            response += f"**Ingredients:** {open_food_facts_data['ingredients_text']}\n"

            if open_food_facts_data.get('allergens'):
                response += f"\n**Allergen:** {open_food_facts_data['allergens']}\n"

            if open_food_facts_data.get('traces'):
                response += f"**May contain traces of:** {open_food_facts_data['traces']}\n"

            response += "\nNote: This from Open Food Facts database, not direct from Trader Joe."
            return response

        # No data found
        return (f"Aiyaa, Uncle Joe cannot find ingredients for '{product_name}' in database. "
               f"Product maybe too new or not have ingredients data yet. "
               f"You can check product label in store or Trader Joe website!")

    def handle_search(self, message: str) -> str:
        """
        Handle product search queries.

        Args:
            message: User message

        Returns:
            Search results in Uncle Joe's voice
        """
        # For search, use the full message but remove common prefixes
        message_lower = message.lower()

        # Remove common search prefixes but keep the meaningful part
        search_prefixes = [
            'what products have ', 'what products contain ',
            'which products have ', 'which products contain ',
            'find me ', 'search for ', 'look for ',
            'show me ', 'do you have ', 'where is ',
            'i want ', 'i need ', 'looking for '
        ]

        query = message_lower
        for prefix in search_prefixes:
            if query.startswith(prefix):
                query = query[len(prefix):]
                break

        # Clean up the query
        query = query.strip('?.,! ')

        if not query:
            return ("What you want Uncle Joe find for you? "
                   "Tell me like 'find cheese' or 'show me vegan products'.")

        # Search products
        results = self.product_search.search(query, limit=5)

        # Format results
        return self.product_search.format_for_uncle_joe(query, results)

    def handle_recipe(self, message: str) -> str:
        """
        Handle recipe generation requests.

        Args:
            message: User message

        Returns:
            Recipe with Uncle Joe's personality
        """
        # Use recipe service with function calling
        return self.recipe_service.generate_recipe(message)

    def handle_chat(self, message: str) -> str:
        """
        Handle general chat with Uncle Joe personality.

        Args:
            message: User message

        Returns:
            Uncle Joe's response
        """
        # Simple rule-based responses for common greetings
        message_lower = message.lower()

        if message_lower in ['hi', 'hello', 'hey']:
            return ("Haiyaa, hello! Welcome to Trader Joe! "
                   "Uncle Joe here to help you find product, check nutrition, or give recipe idea. "
                   "What you need today?")

        if 'thank' in message_lower:
            return "No problem! Uncle Joe happy to help. You come back anytime you need food advice!"

        if message_lower in ['bye', 'goodbye']:
            return "Okay okay, see you next time! Don't forget buy the good ingredient!"

        # Default response for general chat
        return ("Uncle Joe here to help with Trader Joe shopping! "
               "You can ask me:\n"
               "- Product nutrition (like 'calories in Cauliflower Gnocchi')\n"
               "- Find products (like 'find vegan cheese')\n"
               "- Recipe ideas (like 'I want make fried rice')\n\n"
               "What you want know?")

    def chat(self, message: str, history: List[Tuple[str, str]]) -> str:
        """
        Main chat function for Gradio interface.

        Args:
            message: User's message
            history: Chat history (list of [user_msg, bot_msg] pairs)

        Returns:
            Uncle Joe's response
        """
        if not message or not message.strip():
            return "Haiyaa, you don't say anything! Tell Uncle Joe what you want."

        # Detect intent
        intent = self.detect_intent(message)

        # Route to appropriate handler
        if intent == 'off_topic':
            return self.handle_off_topic()
        elif intent == 'nutrition':
            return self.handle_nutrition(message)
        elif intent == 'ingredients':
            return self.handle_ingredients(message)
        elif intent == 'search':
            return self.handle_search(message)
        elif intent == 'recipe':
            return self.handle_recipe(message)
        else:  # chat
            return self.handle_chat(message)


def create_interface():
    """Create and configure Gradio chat interface."""

    # Initialize assistant
    assistant = UncleJoeAssistant()

    # Create Gradio interface
    with gr.Blocks(title="Uncle Joe - Trader Joe's Assistant", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 👨‍🍳 Uncle Joe - Your Trader Joe's Shopping Assistant

        Ask me about:
        - 🥗 **Nutrition** - "What's the nutrition in Cauliflower Gnocchi?"
        - 🔍 **Products** - "Find me vegan cheese"
        - 👨‍🍳 **Recipes** - "I want to make fried rice"

        *Haiyaa! Let's find you good food!*
        """)

        chatbot = gr.Chatbot(
            value=[],
            height=500,
            bubble_full_width=False,
            avatar_images=(None, "👨‍🍳")  # User, Uncle Joe
        )

        with gr.Row():
            msg = gr.Textbox(
                label="Your message",
                placeholder="Ask Uncle Joe about Trader Joe's products, nutrition, or recipes...",
                scale=4
            )
            submit = gr.Button("Send", variant="primary", scale=1)

        with gr.Row():
            clear = gr.Button("Clear Chat")

        gr.Markdown("""
        ### Example Questions:
        - "What's the nutrition in Everything But The Bagel Seasoning?"
        - "Find me some healthy snacks"
        - "I want to make pasta with what's available"
        - "Show me vegan products under $5"
        """)

        # Chat function
        def respond(message, chat_history):
            response = assistant.chat(message, chat_history)
            chat_history.append((message, response))
            return "", chat_history

        # Event handlers
        msg.submit(respond, [msg, chatbot], [msg, chatbot])
        submit.click(respond, [msg, chatbot], [msg, chatbot])
        clear.click(lambda: [], None, chatbot)

    return demo


if __name__ == "__main__":
    print("="*60)
    print("🚀 Starting Uncle Joe Assistant")
    print("="*60)

    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False  # Set to True to create public link
    )
