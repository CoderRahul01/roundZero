"""
List available models for Gemini and Claude APIs.
"""

import sys
from pathlib import Path
import asyncio
import os

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
env_path = backend_dir / ".env"
load_dotenv(env_path)

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from anthropic import AsyncAnthropic


async def list_gemini_models():
    """List available Gemini models."""
    print("=" * 70)
    print("GEMINI MODELS")
    print("=" * 70)
    
    if genai is None:
        print("❌ google-generativeai not installed")
        return
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not configured")
        return
    
    try:
        genai.configure(api_key=api_key)
        
        print("\nAvailable models:")
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods:
                print(f"  ✅ {model.name}")
                print(f"     Description: {model.description[:80]}...")
                print()
    except Exception as e:
        print(f"❌ Error listing models: {e}")


async def list_claude_models():
    """List Claude model information."""
    print("\n" + "=" * 70)
    print("CLAUDE MODELS")
    print("=" * 70)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not configured")
        return
    
    print("\nTrying different Claude model versions:")
    
    models_to_try = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-latest",
        "claude-3-5-sonnet-20240620",
        "claude-3-sonnet-20240229",
        "claude-3-opus-20240229",
        "claude-3-haiku-20240307"
    ]
    
    client = AsyncAnthropic(api_key=api_key)
    
    for model in models_to_try:
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            print(f"  ✅ {model} - AVAILABLE")
        except Exception as e:
            error_str = str(e)
            if "not_found_error" in error_str or "404" in error_str:
                print(f"  ❌ {model} - NOT FOUND")
            else:
                print(f"  ⚠️  {model} - ERROR: {error_str[:50]}...")


async def main():
    """Run model listing."""
    await list_gemini_models()
    await list_claude_models()
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
