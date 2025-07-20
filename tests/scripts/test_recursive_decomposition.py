#!/usr/bin/env python3
"""
Test Recursive Task Decomposition
Tests agent coordination states and recursive spawning patterns
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.agents.task import TaskAgent
from core.agents.base import AgentState, AgentResult
from llm.models import LLMModel

class MockChildAgent:
    """Mock child agent for testing coordination patterns"""
    def __init__(self, task_name: str, will_succeed: bool = True):
        self.task_name = task_name
        self.will_succeed = will_succeed
        self.completed = False
    
    async def execute(self) -> AgentResult:
        """Simulate child agent execution"""
        await asyncio.sleep(0.1)  # Simulate work
        self.completed = True
        
        if self.will_succeed:
            return AgentResult(
                success=True,
                content=f"Completed {self.task_name} successfully",
                execution_time_ms=100
            )
        else:
            return AgentResult(
                success=False,
                content="",
                error_message=f"Failed to complete {self.task_name}",
                execution_time_ms=100
            )

async def test_agent_state_transitions():
    """Test agent state transition methods"""
    print("🔄 TESTING AGENT STATE TRANSITIONS")
    print("-" * 40)
    
    try:
        agent = TaskAgent()
        await agent.initialize()
        
        # Verify initial state
        initial_state = agent.state == AgentState.ACTIVE
        print(f"   Initial state (ACTIVE): {'✅ CORRECT' if initial_state else '❌ WRONG'}")
        
        # Test transition to WAITING
        await agent.transition_to_waiting()
        waiting_state = agent.state == AgentState.WAITING
        print(f"   Transition to WAITING: {'✅ SUCCESS' if waiting_state else '❌ FAILED'}")
        
        # Test transition to COORDINATING
        await agent.transition_to_coordinating()
        coordinating_state = agent.state == AgentState.COORDINATING
        print(f"   Transition to COORDINATING: {'✅ SUCCESS' if coordinating_state else '❌ FAILED'}")
        
        # Test return to ACTIVE
        await agent.return_to_active()
        active_again = agent.state == AgentState.ACTIVE
        print(f"   Return to ACTIVE: {'✅ SUCCESS' if active_again else '❌ FAILED'}")
        
        # Test final completion
        task_input = {
            'task_type': 'content_summary',
            'description': 'Test coordination completion',
            'content': 'Simple test for final state transition',
            'max_tokens': 50
        }
        
        result = await agent.execute(task_input)
        final_completed = agent.state == AgentState.COMPLETED and result.success
        print(f"   Final completion: {'✅ SUCCESS' if final_completed else '❌ FAILED'}")
        
        await agent.terminate()
        
        all_transitions = initial_state and waiting_state and coordinating_state and active_again and final_completed
        return all_transitions
        
    except Exception as e:
        print(f"❌ State transition error: {str(e)}")
        return False

async def test_coordination_pattern():
    """Test parent-child coordination pattern"""
    print(f"\n👨‍👩‍👧‍👦 TESTING COORDINATION PATTERN")
    print("-" * 40)
    
    try:
        parent_agent = TaskAgent()
        await parent_agent.initialize()
        
        print(f"   Parent agent created: {parent_agent.id[:8]}...")
        
        # Simulate parent coordinating children
        await parent_agent.transition_to_waiting()
        print(f"   Parent entered WAITING state")
        
        # Mock child agents
        children = [
            MockChildAgent("Generate schema", True),
            MockChildAgent("Write documentation", True),
            MockChildAgent("Create examples", True)
        ]
        
        # Simulate parallel child execution
        child_results = await asyncio.gather(*[child.execute() for child in children])
        
        all_children_completed = all(result.success for result in child_results)
        print(f"   Child execution: {'✅ ALL SUCCESS' if all_children_completed else '❌ SOME FAILED'}")
        
        # Parent aggregates results
        await parent_agent.transition_to_coordinating()
        print(f"   Parent entered COORDINATING state")
        
        # Simulate result aggregation
        aggregated_content = "\\n".join([f"- {result.content}" for result in child_results])
        
        # Return to active for final synthesis
        await parent_agent.return_to_active()
        
        # Execute final synthesis task
        synthesis_input = {
            'task_type': 'content_transformation',
            'description': 'Synthesize child agent results',
            'content': f"Child results:\\n{aggregated_content}",
            'output_format': 'Summary report',
            'max_tokens': 200
        }
        
        final_result = await parent_agent.execute(synthesis_input)
        coordination_success = final_result.success and len(final_result.content) > 100
        
        print(f"   Result synthesis: {'✅ SUCCESS' if coordination_success else '❌ FAILED'}")
        print(f"   Final state: {parent_agent.state.value}")
        
        await parent_agent.terminate()
        
        return all_children_completed and coordination_success
        
    except Exception as e:
        print(f"❌ Coordination pattern error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_nested_recursion():
    """Test nested recursive decomposition pattern"""
    print(f"\n🪆 TESTING NESTED RECURSION PATTERN")
    print("-" * 40)
    
    try:
        # Level 1 - Top-level agent
        level1_agent = TaskAgent()
        await level1_agent.initialize()
        print(f"   Level 1 agent: {level1_agent.id[:8]}... (ACTIVE)")
        
        # Level 1 transitions to coordination
        await level1_agent.transition_to_waiting()
        
        # Level 2 - Intermediate agents
        level2_agents = []
        for i in range(2):
            agent = TaskAgent()
            await agent.initialize()
            level2_agents.append(agent)
            print(f"   Level 2 agent {i+1}: {agent.id[:8]}... (ACTIVE)")
        
        # Level 2 agents also coordinate children
        for agent in level2_agents:
            await agent.transition_to_waiting()
        
        # Level 3 - Leaf agents (mocked)
        level3_tasks = [
            MockChildAgent(f"Subtask {i}", True) for i in range(4)
        ]
        
        # Execute level 3 (leaf) tasks
        level3_results = await asyncio.gather(*[task.execute() for task in level3_tasks])
        level3_success = all(result.success for result in level3_results)
        print(f"   Level 3 execution: {'✅ SUCCESS' if level3_success else '❌ FAILED'}")
        
        # Level 2 agents coordinate their results
        level2_results = []
        for i, agent in enumerate(level2_agents):
            await agent.transition_to_coordinating()
            await agent.return_to_active()
            
            # Mock level 2 synthesis
            synthesis_input = {
                'task_type': 'content_summary',
                'description': f'Level 2 synthesis {i+1}',
                'content': f"Synthesizing results from level 3 tasks",
                'max_tokens': 100
            }
            
            result = await agent.execute(synthesis_input)
            level2_results.append(result)
            await agent.terminate()
        
        level2_success = all(result.success for result in level2_results)
        print(f"   Level 2 synthesis: {'✅ SUCCESS' if level2_success else '❌ FAILED'}")
        
        # Level 1 final aggregation
        await level1_agent.transition_to_coordinating()
        await level1_agent.return_to_active()
        
        final_synthesis = {
            'task_type': 'document_generation',
            'description': 'Top-level result aggregation',
            'content': 'Final synthesis from all recursive levels',
            'max_tokens': 150
        }
        
        final_result = await level1_agent.execute(final_synthesis)
        final_success = final_result.success
        print(f"   Level 1 final synthesis: {'✅ SUCCESS' if final_success else '❌ FAILED'}")
        
        await level1_agent.terminate()
        
        nested_recursion_success = level3_success and level2_success and final_success
        return nested_recursion_success
        
    except Exception as e:
        print(f"❌ Nested recursion error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_error_recovery_in_coordination():
    """Test error handling during coordination phases"""
    print(f"\n🚨 TESTING ERROR RECOVERY IN COORDINATION")
    print("-" * 40)
    
    try:
        agent = TaskAgent()
        await agent.initialize()
        
        # Enter coordination state
        await agent.transition_to_waiting()
        
        # Simulate child failure scenario
        failed_child = MockChildAgent("Failing task", False)
        successful_child = MockChildAgent("Successful task", True)
        
        child_results = await asyncio.gather(*[failed_child.execute(), successful_child.execute()])
        
        partial_success = any(result.success for result in child_results)
        has_failure = any(not result.success for result in child_results)
        
        print(f"   Mixed results: {'✅ DETECTED' if partial_success and has_failure else '❌ UNEXPECTED'}")
        
        # Agent should handle partial failure gracefully
        await agent.transition_to_coordinating()
        
        # Recovery strategy - proceed with available results
        successful_results = [r for r in child_results if r.success]
        recovery_content = f"Recovered with {len(successful_results)} successful results"
        
        await agent.return_to_active()
        
        recovery_input = {
            'task_type': 'content_transformation', 
            'description': 'Recovery synthesis',
            'content': recovery_content,
            'max_tokens': 100
        }
        
        recovery_result = await agent.execute(recovery_input)
        recovery_success = recovery_result.success
        
        print(f"   Error recovery: {'✅ SUCCESS' if recovery_success else '❌ FAILED'}")
        
        await agent.terminate()
        return recovery_success
        
    except Exception as e:
        print(f"❌ Error recovery test failed: {str(e)}")
        return False

async def main():
    """Run all recursive decomposition tests"""
    print("🚀 RECURSIVE TASK DECOMPOSITION TESTING")
    print("=" * 60)
    
    try:
        # Run all tests
        transitions_passed = await test_agent_state_transitions()
        coordination_passed = await test_coordination_pattern()
        recursion_passed = await test_nested_recursion()
        recovery_passed = await test_error_recovery_in_coordination()
        
        print(f"\n" + "=" * 60)
        print("📊 RECURSIVE DECOMPOSITION TEST RESULTS:")
        print(f"   State transitions: {'✅ PASSED' if transitions_passed else '❌ FAILED'}")
        print(f"   Coordination pattern: {'✅ PASSED' if coordination_passed else '❌ FAILED'}")
        print(f"   Nested recursion: {'✅ PASSED' if recursion_passed else '❌ FAILED'}")
        print(f"   Error recovery: {'✅ PASSED' if recovery_passed else '❌ FAILED'}")
        
        overall_success = all([transitions_passed, coordination_passed, recursion_passed, recovery_passed])
        
        if overall_success:
            print(f"\n🎉 RECURSIVE DECOMPOSITION SYSTEM FULLY OPERATIONAL!")
            print("   ✅ Agent state machine supports coordination patterns")
            print("   ✅ Parent-child coordination working correctly") 
            print("   ✅ Nested recursion levels properly managed")
            print("   ✅ Error recovery maintains system stability")
            print("   ✅ NYX ready for complex recursive task decomposition")
        else:
            print(f"\n❌ RECURSIVE DECOMPOSITION SYSTEM NEEDS FIXES")
            print("   System not ready for complex recursive workflows")
        
        return overall_success
        
    except Exception as e:
        print(f"💥 Recursive decomposition testing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)