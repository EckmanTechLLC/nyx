#!/usr/bin/env python3
"""
Test Agent System Integration
Tests interaction between different agent types and overall system integration
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.agents.task import TaskAgent
from core.agents.council import CouncilAgent
from core.agents.validator import ValidatorAgent
from core.agents.memory import MemoryAgent
from core.agents.base import AgentState
from llm.models import LLMModel

async def test_multi_agent_workflow():
    """Test a workflow involving multiple agent types"""
    print("🔗 TESTING MULTI-AGENT WORKFLOW")
    print("-" * 40)
    
    try:
        # Step 1: Use TaskAgent to generate a document
        task_agent = TaskAgent()
        await task_agent.initialize()
        
        document_task = {
            'task_type': 'document_generation',
            'description': 'Create a technical specification for a new API endpoint',
            'content': 'Create REST API for user authentication with JWT tokens, rate limiting, and input validation',
            'max_tokens': 800
        }
        
        doc_result = await task_agent.execute(document_task)
        doc_success = doc_result.success and len(doc_result.content) > 200
        print(f"   1. Document generation: {'✅ SUCCESS' if doc_success else '❌ FAILED'}")
        
        if not doc_success:
            await task_agent.terminate()
            return False
        
        # Step 2: Use ValidatorAgent to validate the document
        validator_agent = ValidatorAgent()
        await validator_agent.initialize()
        
        validation_task = {
            'content_to_validate': doc_result.content,
            'validation_context': {
                'required_sections': ['authentication', 'endpoint', 'validation'],
                'min_length': 200
            }
        }
        
        validation_result = await validator_agent.execute(validation_task)
        validation_success = validation_result.success  # May pass or fail based on content
        print(f"   2. Document validation: {'✅ COMPLETED' if validation_result.success is not None else '❌ FAILED'}")
        print(f"      Validation passed: {'✅ YES' if validation_success else '❌ NO'}")
        
        # Step 3: Use CouncilAgent to review and improve the document
        council_agent = CouncilAgent()
        await council_agent.initialize()
        
        council_task = {
            'decision_context': f'Review this technical specification and provide recommendations for improvement:\n\n{doc_result.content}',
            'decision_question': 'What improvements should be made to this API specification?',
            'max_tokens_per_member': 400,
            'max_tokens_final': 600
        }
        
        council_result = await council_agent.execute(council_task)
        council_success = council_result.success and 'recommendation' in council_result.content.lower()
        print(f"   3. Council review: {'✅ SUCCESS' if council_success else '❌ FAILED'}")
        
        # Step 4: Use MemoryAgent to store the workflow results
        memory_agent = MemoryAgent()
        await memory_agent.initialize()
        
        memory_task = {
            'operation': 'store',
            'content': f'API Specification Workflow: Generated document ({len(doc_result.content)} chars), Validation: {validation_success}, Council recommendations provided',
            'memory_type': 'decision',
            'scope': 'session',
            'metadata': {
                'workflow_type': 'document_creation',
                'agents_involved': ['task', 'validator', 'council', 'memory'],
                'final_quality': 'reviewed'
            }
        }
        
        memory_result = await memory_agent.execute(memory_task)
        memory_success = memory_result.success
        print(f"   4. Memory storage: {'✅ SUCCESS' if memory_success else '❌ FAILED'}")
        
        # Calculate workflow metrics
        total_tokens = (doc_result.tokens_used + validation_result.tokens_used + 
                       council_result.tokens_used + memory_result.tokens_used)
        total_cost = (doc_result.cost_usd + validation_result.cost_usd + 
                     council_result.cost_usd + memory_result.cost_usd)
        
        print(f"   📊 Workflow metrics:")
        print(f"      Total tokens: {total_tokens:,}")
        print(f"      Total cost: ${total_cost:.6f}")
        print(f"      Agents used: 4")
        
        # Cleanup
        await task_agent.terminate()
        await validator_agent.terminate()
        await council_agent.terminate()
        await memory_agent.terminate()
        
        workflow_success = doc_success and council_success and memory_success
        return workflow_success
        
    except Exception as e:
        print(f"❌ Multi-agent workflow error: {str(e)}")
        return False

async def test_agent_state_consistency():
    """Test that all agent types maintain consistent state behavior"""
    print(f"\n🔄 TESTING AGENT STATE CONSISTENCY")
    print("-" * 40)
    
    try:
        # Create all agent types
        agents = [
            TaskAgent(),
            CouncilAgent(),
            ValidatorAgent(), 
            MemoryAgent()
        ]
        
        agent_names = ['TaskAgent', 'CouncilAgent', 'ValidatorAgent', 'MemoryAgent']
        
        # Test initialization states
        init_results = []
        for agent, name in zip(agents, agent_names):
            init_success = await agent.initialize()
            state_correct = agent.state == AgentState.ACTIVE
            init_results.append(init_success and state_correct)
            print(f"   {name}: {'✅ INITIALIZED' if init_success and state_correct else '❌ FAILED'}")
        
        all_initialized = all(init_results)
        
        # Test termination states
        termination_results = []
        for agent, name in zip(agents, agent_names):
            await agent.terminate()
            state_correct = agent.state == AgentState.TERMINATED
            termination_results.append(state_correct)
            print(f"   {name}: {'✅ TERMINATED' if state_correct else '❌ FAILED'}")
        
        all_terminated = all(termination_results)
        
        state_consistency = all_initialized and all_terminated
        return state_consistency
        
    except Exception as e:
        print(f"❌ State consistency test error: {str(e)}")
        return False

async def test_agent_statistics_consistency():
    """Test that all agents provide consistent statistics"""
    print(f"\n📈 TESTING AGENT STATISTICS CONSISTENCY")
    print("-" * 40)
    
    try:
        # Create and initialize agents
        task_agent = TaskAgent()
        council_agent = CouncilAgent()
        validator_agent = ValidatorAgent()
        memory_agent = MemoryAgent()
        
        agents = [task_agent, council_agent, validator_agent, memory_agent]
        agent_names = ['TaskAgent', 'CouncilAgent', 'ValidatorAgent', 'MemoryAgent']
        
        for agent in agents:
            await agent.initialize()
        
        # Get statistics from each agent
        stats_results = []
        required_base_stats = ['agent_id', 'agent_type', 'state', 'total_executions', 'success_rate']
        
        for agent, name in zip(agents, agent_names):
            stats = await agent.get_statistics()
            has_base_stats = all(key in stats for key in required_base_stats)
            stats_results.append(has_base_stats)
            print(f"   {name}: {'✅ COMPLETE STATS' if has_base_stats else '❌ MISSING STATS'}")
            print(f"      Agent ID: {stats.get('agent_id', 'N/A')[:8]}...")
            print(f"      Type: {stats.get('agent_type', 'N/A')}")
        
        # Test specialized statistics
        council_stats = await council_agent.get_council_statistics()
        has_council_specific = 'council_composition' in council_stats
        print(f"   Council-specific stats: {'✅ PRESENT' if has_council_specific else '❌ MISSING'}")
        
        validator_stats = await validator_agent.get_validator_statistics()
        has_validator_specific = 'validation_level' in validator_stats
        print(f"   Validator-specific stats: {'✅ PRESENT' if has_validator_specific else '❌ MISSING'}")
        
        memory_stats = await memory_agent.get_memory_statistics()
        has_memory_specific = 'memory_retention_days' in memory_stats
        print(f"   Memory-specific stats: {'✅ PRESENT' if has_memory_specific else '❌ MISSING'}")
        
        # Cleanup
        for agent in agents:
            await agent.terminate()
        
        all_stats_consistent = (all(stats_results) and has_council_specific and 
                               has_validator_specific and has_memory_specific)
        return all_stats_consistent
        
    except Exception as e:
        print(f"❌ Statistics consistency test error: {str(e)}")
        return False

async def test_agent_resource_tracking():
    """Test that all agents properly track resource usage"""
    print(f"\n💰 TESTING AGENT RESOURCE TRACKING")
    print("-" * 40)
    
    try:
        # Test resource tracking across different agent types
        task_agent = TaskAgent()
        await task_agent.initialize()
        
        # Execute a simple task
        simple_task = {
            'task_type': 'content_summary',
            'description': 'Summarize this text briefly',
            'content': 'The NYX agent system provides modular AI capabilities through specialized agents.',
            'max_tokens': 100
        }
        
        result = await task_agent.execute(simple_task)
        
        # Validate resource tracking
        has_token_count = result.tokens_used > 0
        has_cost_tracking = result.cost_usd > 0
        has_execution_time = result.execution_time_ms > 0
        
        print(f"   Token tracking: {'✅ WORKING' if has_token_count else '❌ MISSING'}")
        print(f"   Cost tracking: {'✅ WORKING' if has_cost_tracking else '❌ MISSING'}")
        print(f"   Execution timing: {'✅ WORKING' if has_execution_time else '❌ MISSING'}")
        
        print(f"   📊 Resource usage:")
        print(f"      Tokens: {result.tokens_used}")
        print(f"      Cost: ${result.cost_usd:.6f}")
        print(f"      Time: {result.execution_time_ms}ms")
        
        await task_agent.terminate()
        
        resource_tracking_working = has_token_count and has_cost_tracking and has_execution_time
        return resource_tracking_working
        
    except Exception as e:
        print(f"❌ Resource tracking test error: {str(e)}")
        return False

async def main():
    """Run all agent system integration tests"""
    print("🚀 AGENT SYSTEM INTEGRATION TESTING")
    print("=" * 60)
    
    try:
        # Run all integration tests
        workflow_passed = await test_multi_agent_workflow()
        state_passed = await test_agent_state_consistency()
        stats_passed = await test_agent_statistics_consistency()
        resource_passed = await test_agent_resource_tracking()
        
        print(f"\n" + "=" * 60)
        print("📊 INTEGRATION TEST RESULTS:")
        print(f"   Multi-agent workflow: {'✅ PASSED' if workflow_passed else '❌ FAILED'}")
        print(f"   Agent state consistency: {'✅ PASSED' if state_passed else '❌ FAILED'}")
        print(f"   Statistics consistency: {'✅ PASSED' if stats_passed else '❌ FAILED'}")
        print(f"   Resource tracking: {'✅ PASSED' if resource_passed else '❌ FAILED'}")
        
        overall_success = all([workflow_passed, state_passed, stats_passed, resource_passed])
        
        if overall_success:
            print(f"\n🎉 ALL AGENT INTEGRATION TESTS PASSED!")
            print("   ✅ Multi-agent workflows executing successfully")
            print("   ✅ Agent state management consistent across types")
            print("   ✅ Statistics tracking comprehensive and uniform")
            print("   ✅ Resource usage properly tracked and reported")
            print("   ✅ NYX Agent System ready for orchestrator integration")
        else:
            print(f"\n❌ SOME AGENT INTEGRATION TESTS FAILED")
            print("   Integration issues detected - review individual results")
        
        return overall_success
        
    except Exception as e:
        print(f"💥 Agent integration testing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)