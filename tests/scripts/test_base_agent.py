#!/usr/bin/env python3
"""
Test Base Agent Implementation
Tests core agent functionality, LLM integration, and database persistence
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.agents.base import BaseAgent, AgentState, AgentResult
from llm.models import LLMModel

# Create a test implementation of BaseAgent
class TestAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_type="task",  # Use valid agent_type from database constraint
            max_retries=2,
            timeout_seconds=30,
            llm_model=LLMModel.CLAUDE_3_5_HAIKU
        )
    
    async def _agent_specific_initialization(self) -> bool:
        return True
    
    async def _validate_input(self, input_data: dict) -> bool:
        return 'test_prompt' in input_data
    
    async def _agent_specific_execution(self, input_data: dict) -> AgentResult:
        # Test LLM integration
        result = await self._call_llm(
            system_prompt="You are a test assistant.",
            user_prompt=input_data['test_prompt'],
            max_tokens=50,
            temperature=0.7
        )
        return result

async def test_base_agent_functionality():
    """Test base agent core functionality"""
    print("🔍 TESTING BASE AGENT FUNCTIONALITY")
    print("=" * 50)
    
    try:
        # Create a thought tree first to satisfy foreign key constraint
        from database.connection import db_manager
        from database.models import ThoughtTree
        import uuid
        
        thought_tree_id = str(uuid.uuid4())
        
        async with db_manager.get_async_session() as session:
            thought_tree = ThoughtTree(
                id=thought_tree_id,
                goal="Test agent functionality",
                status="in_progress",
                depth=1
            )
            session.add(thought_tree)
            await session.commit()
        
        # Create test agent with thought tree
        agent = TestAgent()
        agent.thought_tree_id = thought_tree_id  # Set required thought tree
        print(f"✅ Agent created: {agent.id[:8]}... (type: {agent.agent_type})")
        
        # Test initialization
        init_success = await agent.initialize()
        print(f"   Initialization: {'✅ SUCCESS' if init_success else '❌ FAILED'}")
        
        if not init_success:
            return False
        
        # Test state management
        expected_state = AgentState.ACTIVE
        actual_state = agent.state
        state_correct = actual_state == expected_state
        print(f"   State management: {'✅ ACTIVE' if state_correct else f'❌ Expected {expected_state}, got {actual_state}'}")
        
        # Test LLM integration
        test_input = {'test_prompt': 'Say "Hello" if you can respond.'}
        execution_result = await agent.execute(test_input)
        
        llm_working = execution_result.success and 'hello' in execution_result.content.lower()
        print(f"   LLM integration: {'✅ WORKING' if llm_working else '❌ FAILED'}")
        print(f"      Response: {execution_result.content[:60]}...")
        print(f"      Tokens used: {execution_result.tokens_used}")
        print(f"      Cost: ${execution_result.cost_usd:.6f}")
        
        # Test database persistence - check if agent actually exists in database
        try:
            from database.connection import db_manager
            from database.models import Agent
            from sqlalchemy import select
            
            async with db_manager.get_async_session() as session:
                result = await session.execute(select(Agent).filter(Agent.id == agent.id))
                db_agent = result.scalar_one_or_none()
                db_persistence = db_agent is not None and db_agent.agent_type == agent.agent_type
        except Exception as e:
            print(f"   Database error: {str(e)}")
            db_persistence = False
            
        print(f"   Database persistence: {'✅ WORKING' if db_persistence else '❌ FAILED'}")
        
        # Test error handling
        invalid_input = {'invalid_field': 'test'}
        error_result = await agent.execute(invalid_input)
        error_handling = not error_result.success and error_result.error_message
        print(f"   Error handling: {'✅ WORKING' if error_handling else '❌ FAILED'}")
        
        # Cleanup
        await agent.terminate()
        termination_success = agent.state == AgentState.TERMINATED
        print(f"   Termination: {'✅ SUCCESS' if termination_success else '❌ FAILED'}")
        
        # Overall assessment
        all_tests_passed = (init_success and state_correct and llm_working and 
                           db_persistence and error_handling and termination_success)
        
        return all_tests_passed
        
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        return False

async def test_agent_retry_logic():
    """Test agent retry and error recovery"""
    print(f"\n🔄 TESTING RETRY LOGIC")
    print("-" * 30)
    
    # Create agent with limited retries
    class FailingAgent(BaseAgent):
        def __init__(self):
            super().__init__(agent_type="validator", max_retries=2)  # Use valid agent_type
            self.attempt_count = 0
        
        async def _agent_specific_initialization(self) -> bool:
            return True
        
        async def _validate_input(self, input_data: dict) -> bool:
            return True
        
        async def _agent_specific_execution(self, input_data: dict) -> AgentResult:
            self.attempt_count += 1
            if self.attempt_count < 3:  # Fail first 2 attempts
                return AgentResult(
                    success=False,
                    content="",
                    error_message=f"Simulated failure on attempt {self.attempt_count}"
                )
            return AgentResult(
                success=True,
                content="Success on final attempt",
                execution_time_ms=100
            )
    
    try:
        agent = FailingAgent()
        await agent.initialize()
        
        result = await agent.execute({'test': 'data'})
        
        # Check if retry logic worked
        retry_success = result.success and agent.attempt_count == 3 and agent.retry_count == 2
        print(f"   Retry logic: {'✅ SUCCESS' if retry_success else '❌ FAILED'}")
        print(f"      Final attempt: {agent.attempt_count}")
        print(f"      Retry count: {agent.retry_count}")
        
        await agent.terminate()
        return retry_success
        
    except Exception as e:
        print(f"❌ Retry test error: {str(e)}")
        return False

async def main():
    """Run all base agent tests"""
    print("🚀 BASE AGENT TESTING")
    print("=" * 60)
    
    try:
        # Run functionality tests
        functionality_passed = await test_base_agent_functionality()
        
        # Run retry logic tests
        retry_passed = await test_agent_retry_logic()
        
        print(f"\n" + "=" * 60)
        print("📊 TEST RESULTS:")
        print(f"   Core functionality: {'✅ PASSED' if functionality_passed else '❌ FAILED'}")
        print(f"   Retry logic: {'✅ PASSED' if retry_passed else '❌ FAILED'}")
        
        overall_success = functionality_passed and retry_passed
        
        if overall_success:
            print(f"\n✅ ALL BASE AGENT TESTS PASSED")
        else:
            print(f"\n❌ BASE AGENT TESTS FAILED")
            if not functionality_passed:
                print("   Core functionality test failed")
            if not retry_passed:
                print("   Retry logic test failed")
        
        return overall_success
        
    except Exception as e:
        print(f"💥 Base agent testing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)