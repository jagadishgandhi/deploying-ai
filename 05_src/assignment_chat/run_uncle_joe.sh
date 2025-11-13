#!/bin/bash
# Helper script to run Uncle Joe with proper environment setup

echo "🚀 Uncle Joe Assistant Launcher"
echo "================================"
echo ""

# Check if API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: OPENAI_API_KEY not set!"
    echo ""
    echo "Please set your OpenAI API key:"
    echo ""
    echo "  export OPENAI_API_KEY='sk-your-key-here'"
    echo ""
    echo "Or run:"
    echo "  OPENAI_API_KEY='sk-your-key' ./run_uncle_joe.sh"
    echo ""
    exit 1
fi

# Check if in correct directory
if [ ! -f "uncle_joe_app.py" ]; then
    echo "❌ Error: Run this from 05_src/assignment_chat directory"
    exit 1
fi

echo "✅ OPENAI_API_KEY is set"
echo ""

# Test ChromaDB
echo "🔍 Checking ChromaDB..."
../../.venv/bin/python3 -c "
import chromadb
try:
    client = chromadb.PersistentClient(path='chroma_db')
    collection = client.get_collection('trader_joes_products')
    print(f'✅ ChromaDB ready: {collection.count()} products')
except Exception as e:
    print(f'❌ ChromaDB error: {e}')
    print('   Run: ../../.venv/bin/python3 scripts/setup_chromadb.py')
    exit(1)
"

echo ""
echo "🎉 Launching Uncle Joe..."
echo "   Open: http://localhost:7860"
echo ""

# Run the app
../../.venv/bin/python3 uncle_joe_app.py
