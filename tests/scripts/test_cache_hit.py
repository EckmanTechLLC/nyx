#!/usr/bin/env python3
"""
Test Cache Hit - Make two calls to verify cache hit detection
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from llm.native_cache import NativePromptCache
from llm.claude_native import ClaudeNativeAPI
from llm.models import LLMModel

async def test_cache_hit_sequence():
    """Test cache creation followed by cache hit"""
    print("🔍 TESTING CACHE HIT SEQUENCE")
    print("=" * 50)
    
    # Create persistent instances
    native_cache = NativePromptCache()
    claude_api = ClaudeNativeAPI(native_cache=native_cache)
    
    # Large prompt for caching
    large_prompt = "You are a comprehensive business analyst with expertise in strategic planning. " * 300  # ~9000 tokens
    
    chars = len(large_prompt)
    estimated_tokens = chars // 4
    print(f"System prompt: {chars:,} characters (~{estimated_tokens:,} tokens)")
    print(f"Should cache: {native_cache.should_cache_content(large_prompt)}")
    
    print(f"\n📞 Call 1 (should create cache):")
    response1 = await claude_api.call_claude(
        system_prompt=large_prompt,
        user_prompt="What are the key strategic priorities?",
        model=LLMModel.CLAUDE_3_5_HAIKU,
        max_tokens=50,
        use_native_caching=True
    )
    
    print(f"   Success: {response1.success}")
    print(f"   Input tokens: {response1.usage.input_tokens}")
    print(f"   Cost: ${response1.usage.cost_usd:.6f}")
    
    # Wait a moment
    await asyncio.sleep(2)
    
    print(f"\n📞 Call 2 (should hit cache):")
    response2 = await claude_api.call_claude(
        system_prompt=large_prompt,  # SAME system prompt
        user_prompt="What are the main risk factors?",  # Different question
        model=LLMModel.CLAUDE_3_5_HAIKU,
        max_tokens=50,
        use_native_caching=True
    )
    
    print(f"   Success: {response2.success}")
    print(f"   Input tokens: {response2.usage.input_tokens}")
    print(f"   Cost: ${response2.usage.cost_usd:.6f}")
    
    # Get statistics
    stats = claude_api.get_statistics()
    cache_stats = stats.get('native_cache_stats', {})
    
    print(f"\n📊 STATISTICS:")
    print(f"   Total requests: {stats.get('total_requests', 0)}")
    print(f"   Cache creation requests: {cache_stats.get('cache_creation_requests', 0)}")
    print(f"   Cache hit requests: {cache_stats.get('cache_hit_requests', 0)}")
    print(f"   Native cache hits (API): {stats.get('native_cache_hits', 0)}")
    print(f"   Input tokens saved: {stats.get('input_tokens_saved', 0):,}")
    print(f"   Cost saved: ${stats.get('cost_saved_by_caching', 0):.6f}")
    
    # Check for success
    both_successful = response1.success and response2.success
    different_responses = response1.content != response2.content
    cache_hits_detected = stats.get('native_cache_hits', 0) > 0
    token_savings = stats.get('input_tokens_saved', 0) > 0
    
    print(f"\n📈 RESULTS:")
    print(f"   Both calls successful: {both_successful}")
    print(f"   Different responses: {different_responses}")
    print(f"   Cache hits detected: {cache_hits_detected}")
    print(f"   Token savings: {token_savings}")
    
    if both_successful and different_responses and cache_hits_detected and token_savings:
        print(f"\n🎉 SUCCESS: Cache hit detection is working!")
        print(f"   ✅ First call created cache")
        print(f"   ✅ Second call hit the cache")
        print(f"   ✅ Both calls returned fresh, unique responses")
        print(f"   ✅ Input token costs reduced through caching")
        return True
    else:
        print(f"\n❌ CACHE HIT TEST FAILED:")
        if not both_successful:
            print(f"   - One or both API calls failed")
        if not different_responses:
            print(f"   - Responses are identical (possible bug)")
        if not cache_hits_detected:
            print(f"   - No cache hits detected by our statistics")
        if not token_savings:
            print(f"   - No token savings detected")
        return False

async def main():
    """Run the test"""
    try:
        success = await test_cache_hit_sequence()
        
        print(f"\n" + "=" * 50)
        if success:
            print(f"✅ CACHE HIT DETECTION IS WORKING!")
        else:
            print(f"❌ Cache hit detection still needs fixes")
        print("=" * 50)
        
        return success
        
    except Exception as e:
        print(f"💥 Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)