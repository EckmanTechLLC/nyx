#!/usr/bin/env python3
"""
Test Memory Agent Implementation
Tests memory storage, retrieval, and database integration
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.agents.memory import MemoryAgent, MemoryScope, MemoryType
from core.agents.base import AgentState

async def test_memory_agent_basic():
    """Test basic memory agent functionality"""
    print("🧠 TESTING MEMORY AGENT BASIC FUNCTIONALITY")
    print("-" * 50)
    
    try:
        # Create memory agent
        agent = MemoryAgent()
        await agent.initialize()
        
        print(f"   Initialization: {'✅ SUCCESS' if agent.state == AgentState.ACTIVE else '❌ FAILED'}")
        
        # Test memory storage
        store_task = {
            'operation': 'store',
            'content': 'Test memory content for basic functionality',
            'memory_type': 'context',
            'scope': 'session',
            'metadata': {'test': True, 'source': 'test_script'}
        }
        
        result = await agent.execute(store_task)
        store_success = result.success
        print(f"   Memory storage: {'✅ SUCCESS' if store_success else '❌ FAILED'}")
        
        if not store_success:
            print(f"      Error: {result.error_message}")
        
        await agent.terminate()
        return store_success
        
    except Exception as e:
        print(f"❌ Memory agent test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_memory_agent_operations():
    """Test different memory operations"""
    print(f"\n💾 TESTING MEMORY OPERATIONS")
    print("-" * 30)
    
    try:
        agent = MemoryAgent()
        await agent.initialize()
        
        # Test different memory types and scopes
        operations = [
            {
                'operation': 'store',
                'content': 'Agent decision context',
                'memory_type': 'decision',
                'scope': 'agent',
                'metadata': {'decision_id': 'test_001'}
            },
            {
                'operation': 'store', 
                'content': 'Learning feedback data',
                'memory_type': 'learning',
                'scope': 'global',
                'metadata': {'feedback_type': 'positive'}
            }
        ]
        
        success_count = 0
        for i, op in enumerate(operations):
            result = await agent.execute(op)
            success = result.success
            success_count += 1 if success else 0
            print(f"   Operation {i+1} ({op['memory_type']}): {'✅ SUCCESS' if success else '❌ FAILED'}")
            if not success:
                print(f"      Error: {result.error_message}")
        
        await agent.terminate()
        return success_count == len(operations)
        
    except Exception as e:
        print(f"❌ Memory operations test error: {str(e)}")
        return False

async def main():
    """Run memory agent tests"""
    print("🚀 MEMORY AGENT TESTING")
    print("=" * 50)
    
    try:
        # Run tests
        basic_passed = await test_memory_agent_basic()
        operations_passed = await test_memory_agent_operations()
        
        print(f"\n" + "=" * 50)
        print("📊 TEST RESULTS:")
        print(f"   Basic functionality: {'✅ PASSED' if basic_passed else '❌ FAILED'}")
        print(f"   Memory operations: {'✅ PASSED' if operations_passed else '❌ FAILED'}")
        
        overall_success = basic_passed and operations_passed
        
        if overall_success:
            print(f"\n✅ MEMORY AGENT TESTS PASSED")
        else:
            print(f"\n❌ MEMORY AGENT TESTS FAILED")
            print("   Memory agent has database integration issues")
        
        return overall_success
        
    except Exception as e:
        print(f"💥 Memory agent testing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)