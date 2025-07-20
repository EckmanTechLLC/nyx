#!/usr/bin/env python3
"""
Test Real Cache Detection - Verify cache hit detection using real Claude API response data
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

async def test_real_cache_detection():
    """Test cache detection using real API response data"""
    print("🔍 TESTING REAL CACHE DETECTION")
    print("=" * 50)
    
    # Create single instance for consistent tracking
    native_cache = NativePromptCache()
    claude_api = ClaudeNativeAPI(native_cache=native_cache)
    
    # Large prompt to ensure caching (6000+ tokens)
    large_system_prompt = """
You are a comprehensive business intelligence and strategic advisory system with deep expertise across multiple critical business domains including strategic planning, financial analysis and modeling, market research and competitive intelligence, regulatory compliance and legal frameworks, technology infrastructure and scalability assessment, operational excellence and process optimization, risk management and mitigation strategies, organizational development and change management, strategic partnerships and business development, and comprehensive performance metrics and KPI optimization.

Your extensive analytical capabilities encompass advanced financial modeling including DCF models, scenario planning, sensitivity analysis, Monte Carlo simulations, and risk-adjusted return calculations; comprehensive market opportunity assessment including total addressable market (TAM), serviceable addressable market (SAM), and serviceable obtainable market (SOM) analysis, competitive landscape mapping, customer segmentation analysis, market penetration strategies, and growth trajectory modeling; regulatory and compliance framework analysis covering data protection regulations such as GDPR and CCPA, industry-specific compliance requirements, international trade regulations, intellectual property protection strategies, and regulatory risk assessment; technology infrastructure evaluation including cloud architecture assessment, scalability planning, security framework analysis, system integration capabilities, API design and management, database optimization, and technology stack recommendations; operational excellence planning covering lean process optimization, supply chain management, quality assurance frameworks, inventory management, logistics optimization, and comprehensive performance measurement systems.

Your risk assessment and mitigation expertise includes political risk analysis, economic volatility assessment, competitive threat evaluation, operational risk management, cybersecurity risk assessment, regulatory compliance risks, reputational risk management, and comprehensive business continuity planning; organizational development capabilities including talent acquisition strategies, cultural transformation initiatives, leadership development programs, employee engagement optimization, change management methodologies, succession planning, and organizational structure optimization; strategic partnership evaluation including joint venture analysis, licensing agreement evaluation, distribution partnership assessment, merger and acquisition opportunity analysis, strategic alliance formation, and partnership risk evaluation.

Your industry-specific expertise spans Software as a Service (SaaS) platforms including subscription model optimization, customer acquisition cost analysis, customer lifetime value maximization, churn reduction strategies, product-led growth implementation, multi-tenant architecture scaling, and SaaS metrics optimization; financial technology including regulatory compliance navigation, payment processing optimization, fraud prevention systems, cross-border transaction frameworks, cryptocurrency integration, blockchain applications, and fintech security protocols; healthcare technology including HIPAA compliance management, clinical workflow integration, electronic health record optimization, patient data protection, FDA regulatory processes, medical device compliance, and healthcare interoperability standards; e-commerce platforms including conversion rate optimization, customer experience enhancement, payment gateway integration, inventory management systems, international logistics coordination, mobile commerce optimization, and omnichannel strategy implementation.
""" * 3

    chars = len(large_system_prompt)
    estimated_tokens = chars // 4
    should_cache = native_cache.should_cache_content(large_system_prompt)
    
    print(f"System prompt: {chars:,} characters (~{estimated_tokens:,} tokens)")
    print(f"Should cache: {should_cache}")
    
    if not should_cache:
        print("❌ ERROR: Prompt too small for caching test")
        return False
    
    questions = [
        "What are the key strategic priorities for market expansion?",
        "What financial metrics should we track for growth?",
        "What are the main operational challenges we should expect?"
    ]
    
    print(f"\n🔄 Making 3 calls with same system prompt...")
    
    responses = []
    for i, question in enumerate(questions, 1):
        print(f"\n📞 Call {i}: {question[:40]}...")
        
        response = await claude_api.call_claude(
            system_prompt=large_system_prompt,
            user_prompt=question,
            model=LLMModel.CLAUDE_3_5_HAIKU,
            max_tokens=100,
            use_native_caching=True
        )
        
        responses.append(response)
        
        if response.success:
            print(f"   ✅ Success: {response.content[:50]}...")
            print(f"   Input tokens: {response.usage.input_tokens}")
            print(f"   Cost: ${response.usage.cost_usd:.6f}")
        else:
            print(f"   ❌ Failed: {response.error_message}")
    
    # Get final statistics
    stats = claude_api.get_statistics()
    cache_stats = stats.get('native_cache_stats', {})
    
    print(f"\n📊 REAL CACHE DETECTION RESULTS:")
    print(f"   Total requests: {stats.get('total_requests', 0)}")
    print(f"   Cache creation requests: {cache_stats.get('cache_creation_requests', 0)}")
    print(f"   Cache hit requests: {cache_stats.get('cache_hit_requests', 0)}")
    print(f"   Native cache hits (API reported): {stats.get('native_cache_hits', 0)}")
    print(f"   Input tokens saved: {stats.get('input_tokens_saved', 0):,}")
    print(f"   Cost saved: ${stats.get('cost_saved_by_caching', 0):.6f}")
    
    # Calculate hit rate
    total_requests = stats.get('total_requests', 0)
    cache_hits = stats.get('native_cache_hits', 0)
    hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0
    
    print(f"\n📈 ANALYSIS:")
    print(f"   Cache hit rate: {hit_rate:.1f}% ({cache_hits}/{total_requests})")
    
    # Success criteria - we need ACTUAL cache hits, not just requests
    all_successful = all(r.success for r in responses)
    fresh_responses = len(set(r.content for r in responses)) == len(responses)  # All different
    actual_cache_hits = cache_hits > 0  # Must have real API-reported cache hits
    
    print(f"   All calls successful: {all_successful}")
    print(f"   All responses unique: {fresh_responses}")
    print(f"   Actual cache hits from API: {actual_cache_hits}")
    
    if all_successful and fresh_responses and actual_cache_hits:
        print(f"\n🎉 SUCCESS: Real cache detection is working!")
        print(f"   ✅ Claude's API reported cache hits in response")
        print(f"   ✅ Cache hits properly detected from server-side usage")
        print(f"   ✅ Fresh responses generated while reusing cached context")
        return True
    else:
        print(f"\n❌ CACHE DETECTION FAILED:")
        if not all_successful:
            print(f"   - Some API calls failed")
        if not fresh_responses:
            print(f"   - Responses are not unique (possible response caching bug)")
        if not actual_cache_hits:
            print(f"   - Claude API returned 0 cache hits - caching not working!")
            print(f"   - Cache creation tokens: {cache_stats.get('cache_creation_requests', 0)}")
            print(f"   - This means cache_control parameters may be incorrect")
        return False

async def main():
    """Run the test"""
    try:
        success = await test_real_cache_detection()
        
        print(f"\n" + "=" * 50)
        if success:
            print(f"✅ CACHE DETECTION FIXED - Using real Claude API data!")
        else:
            print(f"❌ Cache detection still has issues")
        print("=" * 50)
        
        return success
        
    except Exception as e:
        print(f"💥 Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)