# Uncle Joe - Trader Joe's AI Shopping Assistant

**Assignment 2: AI System with Conversational Interface**

An entertaining and helpful AI shopping assistant for Trader Joe's with Uncle Roger-inspired personality.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Three Required Services](#three-required-services)
- [Installation](#installation)
- [Data Collection & Processing Pipeline](#data-collection--processing-pipeline)
- [Embedding Process](#embedding-process)
- [Usage](#usage)
- [Guardrails](#guardrails)
- [Project Structure](#project-structure)
- [Assignment Requirements](#assignment-requirements)

---

## Overview

Uncle Joe is an AI-powered shopping assistant that helps users:
- Find Trader Joe's products using natural language
- Get nutritional information from Open Food Facts API
- Check ingredients and allergens
- Discover recipe ideas using available products

**Unique Personality**: Uncle Joe combines Uncle Roger's entertaining style with helpful grocery advice, using simplified English grammar patterns and signature phrases like "Haiyaa" and "Fuiyoh!"

---

## Features

### 1. Semantic Product Search
- Natural language queries: "show me plant-based items under $5"
- Price filtering and category browsing
- Vector similarity-based search using OpenAI embeddings

### 2. Nutritional Analysis
- Real-time nutritional information via Open Food Facts API
- Calorie, macro, and micronutrient information
- No API key required - completely free and open
- Transformed into Uncle Joe's conversational voice

### 3. Recipe Generation
- AI-powered recipe suggestions using function calling
- Uses actual Trader Joe's products
- Step-by-step instructions in Uncle Joe's voice

### 4. Engaging Chat Interface
- Gradio-based conversational UI
- Maintains conversation memory
- Entertaining personality with helpful advice

---

## Three Required Services

### Service 1: Nutrition API Service (Requirement #1: API Calls)

**File:** `services/nutrition_service.py`

**API**: [Open Food Facts API](https://world.openfoodfacts.org/) - completely free, no authentication required

**Purpose**: Provide detailed nutritional information for Trader Joe's products

**Implementation**:
- Searches Open Food Facts database for products by name
- Extracts calories, protein, fat, carbs, fiber, vitamins, minerals
- Retrieves ingredients and allergen information
- Transforms structured API response into Uncle Joe's conversational voice (not verbatim)

**API Details**:
- Endpoint: `https://world.openfoodfacts.org/cgi/search.pl`
- Free tier: Unlimited (open database)
- Response transformed into natural language with personality

---

### Service 2: Product Search Service (Requirement #2: Semantic Query)

**File:** `services/product_search_service.py`

**Backend**: ChromaDB with Persistent File Storage

**Purpose**: Enable natural language product search across Trader Joe's catalog

**Dataset Details**:
- **Source**: Web-scraped Trader Joe's product data
- **Size**: ~15 products (test dataset), expandable to 1500+ products
- **Format**: ChromaDB persistent client (file-based, not Docker)
- **Embeddings**: Pre-computed using OpenAI text-embedding-3-small (1536 dimensions)

**Features**:
- Semantic search with vector embeddings
- Hybrid filtering: Vector similarity + metadata (price, category)
- Cosine similarity for relevance ranking
- Fallback to metadata search when API unavailable

**Example Interaction**:
```
User: "Show me plant-based snacks under $5"

Uncle Joe: "Fuiyoh! Uncle Joe find 3 items for you:

1. Organic Roasted Plantain Chips - $2.99 (Snacks) - Haiyaa, very cheap!
2. Edamame - $1.99 (Frozen) - High protein, very healthy
3. Hummus Trio Pack - $4.99 (Dips & Spreads) - Good for dipping vegetable

Which one you want know more about? Uncle Joe can tell you nutrition or give recipe idea!"
```

---

### Service 3: Recipe Service (Requirement #3: Function Calling)

**File:** `services/recipe_service.py`

**Type**: OpenAI Function Calling with GPT-4o-mini

**Purpose**: Generate recipes using available Trader Joe's products with autonomous tool use

**Functions Defined**:
- `search_products_for_recipe(query, category)` - Search for products needed in recipe

**How It Works**:
1. User requests a recipe (e.g., "give me a quick dinner recipe")
2. GPT-4o-mini determines what ingredients are needed
3. Autonomously calls `search_products_for_recipe` to find products
4. Receives actual Trader Joe's products with prices
5. Generates complete recipe using those specific products

**Example Interaction**:
```
User: "Give me a quick pasta recipe"

Uncle Joe: "Okay! Uncle Joe make you easy pasta recipe...
[Internally calls: search_products_for_recipe("pasta")]
[Internally calls: search_products_for_recipe("pasta sauce")]
[Internally calls: search_products_for_recipe("cheese")]

Fuiyoh! Uncle Joe Quick Pasta - 15 Minute!

Ingredients from Trader Joe:
- Organic Penne Pasta ($2.49)
- Tomato Basil Marinara ($2.99)
- Shredded Mozzarella ($3.99)
- Fresh Basil ($2.49)

Total cost: $11.96 (make 4 serving = $2.99 each!)

Instructions:
1. Boil pasta 9-10 minute - don't overcook!
2. Heat sauce in pan
3. Drain pasta, mix with sauce
4. Add cheese on top
5. Garnish with basil

Uncle Joe tip: Save pasta water! Add little bit to sauce if too thick."
```

---

## Installation

### Prerequisites
- Python 3.10+
- OpenAI API key
- Playwright (for scraping - optional)

### Steps

1. **Install dependencies**:
```bash
# Navigate to project directory
cd 05_src/assignment_chat

# Install Playwright browsers (only if running scrapers)
playwright install chromium
```

2. **Set environment variables**:
```bash
# Set OpenAI API key
export OPENAI_API_KEY='your-key-here'
```

3. **Setup data** (if starting fresh):
```bash
# Step 1: Collect product URLs
python scripts/scrape_product_urls.py

# Step 2: Scrape product details
python scripts/scrape_product_details.py

# Step 3: Generate embeddings
python scripts/create_embeddings_enhanced.py

# Step 4: Setup ChromaDB
python scripts/setup_chromadb.py
```

4. **Run the application**:
```bash
python uncle_joe_app.py
```

Access at: `http://localhost:7860`

---

## Data Collection & Processing Pipeline

### Pipeline Overview

**1. URL Collection** → **2. Product Scraping** → **3. Embedding Generation** → **4. ChromaDB Setup**

### Step 1: Product URL Collection

**Script:** `scripts/scrape_product_urls.py`

**Purpose:** Collects product URLs from Trader Joe's website

**Features:**
- Uses Playwright for JavaScript-rendered pages
- Anti-detection techniques (custom user agent, stealth scripts)
- Handles pagination automatically
- Saves to `data/product_urls.json`

**Output:** JSON file with URLs and tracking metadata

---

### Step 2: Product Details Scraping

**Script:** `scripts/scrape_product_details.py`

**Purpose:** Scrapes comprehensive product details from each URL

**Extracted Data:**
- Product name, price, category, description
- **Ingredients**: Extracted from `<li>` elements in ingredient lists
- **Allergens**: Split into `allergens_contains` and `allergens_may_contain` arrays
- **Nutrition**: Full nutrition facts (calories, protein, fat, carbs, vitamins, minerals)
- Tags and special flags

**Features:**
- Resume capability (tracks scraped URLs)
- Saves after each product to prevent data loss
- Error handling and retry logic

**Output:** `data/tj_products_full.json`

---

### Step 3: Embeddings Generation

**Script:** `scripts/create_embeddings_enhanced.py`

**Purpose:** Generate OpenAI embeddings for semantic search

**Process:**
1. Loads products from `data/tj_products_full.json`
2. Creates comprehensive text representation including:
   - Product name and category
   - Description (truncated to 500 chars)
   - Tags
   - Ingredients (first 300 chars)
   - Allergen information
   - Nutrition highlights
3. Generates embeddings using OpenAI `text-embedding-3-small`
4. Processes in batches of 50 for efficiency

**Requirements:**
- OpenAI API key
- Input: `data/tj_products_full.json`

**Output:** `data/tj_products_with_embeddings.json`

---

### Step 4: ChromaDB Setup

**Script:** `scripts/setup_chromadb.py`

**Purpose:** Load embeddings into ChromaDB for vector search

**Features:**
- Creates persistent ChromaDB collection
- Uses cosine similarity metric
- Stores metadata (name, price, category, URL)
- Processes in batches of 100
- Interactive mode (prompts before overwriting)

**Important Notes:**
- Uses `collection.add()` (no upsert support)
- Answer 'y' to reset prompt for fresh data
- Includes test search to verify setup

**Output:** `chroma_db/` directory with vector database

---

## Embedding Process

### Detailed Embedding Generation

**Model**: OpenAI `text-embedding-3-small`
**Dimensions**: 1536

### Example Product Text Representation:
```
Product: Unexpected Cheddar | Category: Cheese | Price: $4.99 |
Description: A cheddar that gets better with age, revealing crystalline
pockets of flavor... | Tags: Vegetarian, Award Winner | Allergens: Milk
```

### File Sizes:
- Raw product data: ~36 KB (15 products)
- With embeddings: ~700 KB
- ChromaDB database: ~45 MB ⚠️ (exceeds 40 MB limit - needs optimization)
---

## Usage

### Starting the Chat

```bash
cd 05_src/assignment_chat
python uncle_joe_app.py
```

Opens Gradio interface at `http://localhost:7860`

### Forbidden Topics

Uncle Joe won't discuss:
- ❌ Cats or dogs
- ❌ Horoscopes or Zodiac signs
- ❌ Taylor Swift

**Response**: "Aiyaa, Uncle Joe only talk about food! What you want to eat?"


## Project Structure

```
05_src/assignment_chat/
├── README.md                          # This file
├── uncle_joe_app.py                   # Main Gradio application
├── run_uncle_joe.sh                   # Convenience launcher script
│
├── services/
│   ├── __init__.py
│   ├── nutrition_service.py           # Service 1: Open Food Facts API
│   ├── product_search_service.py      # Service 2: ChromaDB search
│   └── recipe_service.py              # Service 3: Function calling
│
├── scripts/
│   ├── scrape_product_urls.py         # Step 1: URL collection
│   ├── scrape_product_details.py      # Step 2: Product scraping
│   ├── create_embeddings_enhanced.py  # Step 3: Embedding generation
│   ├── setup_chromadb.py              # Step 4: ChromaDB setup
│   └── rescrape_failed.py             # Utility: Retry failed products
│
├── data/
│   ├── product_urls.json              # Collected URLs
│   ├── tj_products_full.json          # Scraped products (36 KB)
│   └── tj_products_with_embeddings.json  # With embeddings (700 KB)
│
└── chroma_db/                         # ChromaDB storage (45 MB)
    └── [auto-generated files]
```

## Acknowledgments

- **Trader Joe's**: Product data source
- **Open Food Facts**: Free nutrition API
- **Uncle Roger (Nigel Ng)**: Personality inspiration

---

## License

Educational use only - Assignment 2 for Deploying AI course.

**Disclaimer**: This project is for educational purposes. Trader Joe's products and descriptions are property of Trader Joe's. Uncle Roger is a character created by Nigel Ng.

---

*Last Updated: November 9, 2025*
*Author: Jagadish Gandhi*
*Course: Deploying AI - University of Toronto*
