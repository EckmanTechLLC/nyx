#!/usr/bin/env python3
"""
Debug Cache API - Investigate why Claude API returns 0 cache tokens
"""
import asyncio
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from llm.native_cache import NativePromptCache
from llm.claude_native import ClaudeNativeAPI
from llm.models import LLMModel

async def debug_claude_response():
    """Debug the actual Claude API response to see cache data"""
    print("🔍 DEBUGGING CLAUDE API CACHE RESPONSE")
    print("=" * 50)
    
    # Create instances
    native_cache = NativePromptCache()
    claude_api = ClaudeNativeAPI(native_cache=native_cache)
    
    # Large prompt that should definitely be cached
    large_prompt = "You are a comprehensive business analyst. " * 500  # ~10,000 tokens
    
    chars = len(large_prompt)
    estimated_tokens = chars // 4
    print(f"System prompt: {chars:,} characters (~{estimated_tokens:,} tokens)")
    print(f"Should cache: {native_cache.should_cache_content(large_prompt)}")
    
    # Check what we're sending to Claude
    system_messages = native_cache.create_cached_system_prompt(large_prompt)
    print(f"\n📤 SYSTEM MESSAGES BEING SENT:")
    for i, msg in enumerate(system_messages):
        print(f"   {i+1}. Type: {msg.get('type')}")
        print(f"      Text length: {len(msg.get('text', ''))}")
        print(f"      Cache control: {msg.get('cache_control')}")
    
    # Make call and inspect raw response
    print(f"\n📞 Making API call...")
    
    try:
        # We need to modify the call to inspect the raw response
        # Let's make a direct call to see what Claude returns
        from anthropic import AsyncAnthropic
        from config.settings import settings
        
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        
        # Direct API call with caching
        raw_response = await client.messages.create(
            model=LLMModel.CLAUDE_3_5_HAIKU.value,
            max_tokens=50,
            temperature=0.7,
            system=system_messages,
            messages=[{"role": "user", "content": "What is the key insight?"}],
            extra_headers={
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "prompt-caching-2024-07-31"
            }
        )
        
        print(f"\n📥 RAW CLAUDE API RESPONSE:")
        print(f"   Response type: {type(raw_response)}")
        print(f"   Response dir: {[attr for attr in dir(raw_response) if not attr.startswith('_')]}")
        
        print(f"\n📊 USAGE OBJECT:")
        usage = raw_response.usage
        print(f"   Usage type: {type(usage)}")
        print(f"   Usage dir: {[attr for attr in dir(usage) if not attr.startswith('_')]}")
        print(f"   Usage dict: {usage.__dict__ if hasattr(usage, '__dict__') else 'No __dict__'}")
        
        print(f"\n💾 USAGE VALUES:")
        print(f"   input_tokens: {getattr(usage, 'input_tokens', 'NOT FOUND')}")
        print(f"   output_tokens: {getattr(usage, 'output_tokens', 'NOT FOUND')}")
        print(f"   cache_creation_input_tokens: {getattr(usage, 'cache_creation_input_tokens', 'NOT FOUND')}")
        print(f"   cache_read_input_tokens: {getattr(usage, 'cache_read_input_tokens', 'NOT FOUND')}")
        
        # Try to convert to dict/json to see all fields
        try:
            usage_dict = usage.model_dump() if hasattr(usage, 'model_dump') else usage.__dict__
            print(f"\n📋 COMPLETE USAGE DATA:")
            print(json.dumps(usage_dict, indent=2, default=str))
        except Exception as e:
            print(f"   Could not serialize usage: {e}")
        
        print(f"\n📄 RESPONSE CONTENT:")
        print(f"   Content: {raw_response.content[0].text[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"💥 API call failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the debug"""
    try:
        success = await debug_claude_response()
        
        print(f"\n" + "=" * 50)
        if success:
            print(f"✅ Debug completed - check output above for cache data")
        else:
            print(f"❌ Debug failed")
        print("=" * 50)
        
        return success
        
    except Exception as e:
        print(f"💥 Debug failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)