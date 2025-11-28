"""
Simple example of using Lovable.dev workflow components.

This script demonstrates:
1. Loading OpenAI API key from .env
2. Generating a prompt with OpenAI
3. Creating a Lovable.dev URL

Run with: python test-workflow/test_lovable_simple.py
"""
import asyncio
import os
import sys

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path)
except ImportError:
    pass

from openai import AsyncOpenAI
import urllib.parse

# Import from main workflow (same directory)
from test_lovable_workflow import LovablePromptGenerator, LovablePrototypeGenerator

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY not found in .env file")
    sys.exit(1)


async def simple_example():
    """Simple example of generating a Lovable.dev URL."""
    print("=" * 80)
    print("SIMPLE LOVABLE.DEV EXAMPLE")
    print("=" * 80)
    
    # Product description
    product_description = "A todo app with drag-and-drop tasks, categories, and due dates"
    
    # Generate prompt
    print("\n📝 Generating prompt with OpenAI...")
    prompt_generator = LovablePromptGenerator(OPENAI_API_KEY)
    prompt = await prompt_generator.generate_prompt(product_description)
    
    print(f"✅ Generated prompt:")
    print("-" * 80)
    print(prompt)
    print("-" * 80)
    
    # Generate Lovable.dev URL
    print("\n🔗 Generating Lovable.dev URL...")
    prototype_generator = LovablePrototypeGenerator()
    lovable_url = prototype_generator.build_lovable_url(prompt)
    
    print(f"✅ Lovable.dev URL:")
    print("-" * 80)
    print(lovable_url)
    print("-" * 80)
    print("\n💡 Open this URL in your browser to generate the prototype!")
    print("   After generation, you'll be redirected to the prototype URL.")
    
    return lovable_url


if __name__ == "__main__":
    asyncio.run(simple_example())
