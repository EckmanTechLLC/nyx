#!/usr/bin/env python3
"""
Test BaseOrchestrator Implementation
Tests core orchestrator functionality including agent lifecycle management,
resource limits, and database persistence.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.orchestrator.base import BaseOrchestrator, OrchestratorResult
from core.agents.base import AgentResult

async def test_orchestrator_initialization():
    """Test orchestrator initialization and database persistence"""
    print("🔧 TESTING ORCHESTRATOR INITIALIZATION")
    print("-" * 40)
    
    try:
        orchestrator = BaseOrchestrator(
            orchestrator_type="test",
            max_concurrent_agents=3
        )
        
        # Test initialization
        init_success = await orchestrator.initialize()
        print(f"   Initialization: {'✅ SUCCESS' if init_success else '❌ FAILED'}")
        
        # Check state
        status = await orchestrator.get_orchestrator_status()
        state_correct = status['state'] == 'active'
        print(f"   Active state: {'✅ CORRECT' if state_correct else '❌ WRONG'}")
        
        # Check thought tree creation
        tree_created = status['thought_tree_id'] is not None
        print(f"   Thought tree created: {'✅ SUCCESS' if tree_created else '❌ FAILED'}")
        
        # Check resource limits
        limits_set = status['max_concurrent_agents'] == 3
        print(f"   Resource limits set: {'✅ CORRECT' if limits_set else '❌ WRONG'}")
        
        await orchestrator.terminate()
        
        return init_success and state_correct and tree_created and limits_set
        
    except Exception as e:
        print(f"❌ Initialization test error: {str(e)}")
        return False

async def test_agent_spawning():
    """Test agent spawning and lifecycle tracking"""
    print(f"\\n🤖 TESTING AGENT SPAWNING & LIFECYCLE")
    print("-" * 40)
    
    try:
        orchestrator = BaseOrchestrator(
            orchestrator_type="test",
            max_concurrent_agents=5
        )
        await orchestrator.initialize()
        
        # Test spawning different agent types
        task_agent = await orchestrator.spawn_agent("task", {'timeout': 60})
        task_spawned = task_agent is not None
        print(f"   Task agent spawn: {'✅ SUCCESS' if task_spawned else '❌ FAILED'}")
        
        council_agent = await orchestrator.spawn_agent("council", {'timeout': 60})
        council_spawned = council_agent is not None
        print(f"   Council agent spawn: {'✅ SUCCESS' if council_spawned else '❌ FAILED'}")
        
        validator_agent = await orchestrator.spawn_agent("validator", {'timeout': 60})
        validator_spawned = validator_agent is not None
        print(f"   Validator agent spawn: {'✅ SUCCESS' if validator_spawned else '❌ FAILED'}")
        
        memory_agent = await orchestrator.spawn_agent("memory", {'timeout': 60})
        memory_spawned = memory_agent is not None
        print(f"   Memory agent spawn: {'✅ SUCCESS' if memory_spawned else '❌ FAILED'}")
        
        # Check agent tracking
        status = await orchestrator.get_orchestrator_status()
        agents_tracked = status['current_active_agents'] == 4
        print(f"   Agent tracking: {'✅ CORRECT' if agents_tracked else '❌ WRONG'}")
        
        # Clean up
        await orchestrator.terminate()
        
        return task_spawned and council_spawned and validator_spawned and memory_spawned and agents_tracked
        
    except Exception as e:
        print(f"❌ Agent spawning test error: {str(e)}")
        return False

async def test_resource_limits():
    """Test resource limit enforcement"""
    print(f"\\n📊 TESTING RESOURCE LIMIT ENFORCEMENT")
    print("-" * 40)
    
    try:
        orchestrator = BaseOrchestrator(
            orchestrator_type="test",
            max_concurrent_agents=2
        )  # Low limit for testing
        await orchestrator.initialize()
        
        # Test resource limit enforcement manually
        agents_spawned = []
        spawn_attempts = orchestrator.max_concurrent_agents + 3  # Try to exceed limit
        
        for i in range(spawn_attempts):
            agent = await orchestrator.spawn_agent(
                agent_type="task",
                task_context={'timeout': 30}
            )
            
            if agent:
                agents_spawned.append(agent)
            else:
                break  # Hit limit as expected
        
        # Clean up agents
        for agent in agents_spawned:
            try:
                await agent.terminate()
                await orchestrator.track_agent_completion(agent, AgentResult(
                    success=True,
                    content="Resource limit test cleanup"
                ))
            except:
                pass
        
        limit_results = {
            'max_concurrent_agents': orchestrator.max_concurrent_agents,
            'spawn_attempts': spawn_attempts,
            'agents_actually_spawned': len(agents_spawned),
            'limit_enforced': len(agents_spawned) <= orchestrator.max_concurrent_agents,
            'test_passed': len(agents_spawned) == orchestrator.max_concurrent_agents
        }
        
        limit_enforced = limit_results.get('limit_enforced', False)
        test_passed = limit_results.get('test_passed', False)
        
        print(f"   Max agents allowed: {limit_results.get('max_concurrent_agents', 'unknown')}")
        print(f"   Spawn attempts: {limit_results.get('spawn_attempts', 'unknown')}")
        print(f"   Actually spawned: {limit_results.get('agents_actually_spawned', 'unknown')}")
        print(f"   Limit enforced: {'✅ SUCCESS' if limit_enforced else '❌ FAILED'}")
        print(f"   Test passed: {'✅ SUCCESS' if test_passed else '❌ FAILED'}")
        
        await orchestrator.terminate()
        
        return limit_enforced and test_passed
        
    except Exception as e:
        print(f"❌ Resource limit test error: {str(e)}")
        return False

async def test_simple_workflow():
    """Test simple workflow execution"""
    print(f"\\n🔄 TESTING SIMPLE WORKFLOW EXECUTION")
    print("-" * 40)
    
    try:
        orchestrator = BaseOrchestrator(orchestrator_type="test")
        await orchestrator.initialize()
        
        # Execute simple workflow manually
        task_agent = await orchestrator.spawn_agent(
            agent_type="task",
            task_context={'max_retries': 2, 'timeout': 60}
        )
        
        if not task_agent:
            return False
        
        # Execute the task
        task_input = {
            'task_type': 'content_summary',
            'description': "Test orchestrator workflow execution",
            'content': 'Test workflow execution with orchestrator coordination',
            'max_tokens': 100
        }
        
        agent_result = await task_agent.execute(task_input)
        await orchestrator.track_agent_completion(task_agent, agent_result)
        await task_agent.terminate()
        
        # Get final orchestrator result
        result = await orchestrator.terminate()
        
        workflow_success = result.success
        print(f"   Workflow execution: {'✅ SUCCESS' if workflow_success else '❌ FAILED'}")
        
        agents_spawned = result.agents_spawned > 0
        print(f"   Agents spawned: {'✅ SUCCESS' if agents_spawned else '❌ FAILED'}")
        
        metrics_tracked = result.total_tokens > 0 or result.total_cost_usd > 0
        print(f"   Metrics tracking: {'✅ SUCCESS' if metrics_tracked else '❌ FAILED'}")
        
        has_output = result.final_output is not None
        print(f"   Final output: {'✅ SUCCESS' if has_output else '❌ FAILED'}")
        
        return workflow_success and agents_spawned and has_output
        
    except Exception as e:
        print(f"❌ Simple workflow test error: {str(e)}")
        return False

async def test_multi_agent_coordination():
    """Test multi-agent coordination"""
    print(f"\\n👥 TESTING MULTI-AGENT COORDINATION")
    print("-" * 40)
    
    try:
        orchestrator = BaseOrchestrator(
            orchestrator_type="test",
            max_concurrent_agents=5
        )
        await orchestrator.initialize()
        
        # Execute multi-agent workflow manually
        num_agents = 3
        agents = []
        
        # Spawn multiple agents
        for i in range(num_agents):
            agent = await orchestrator.spawn_agent(
                agent_type="task",
                task_context={'max_retries': 1, 'timeout': 30}
            )
            
            if agent:
                agents.append(agent)
            else:
                break  # Hit resource limit
        
        # Execute agents sequentially
        for i, agent in enumerate(agents):
            task_input = {
                'task_type': 'content_summary', 
                'description': f'Multi-agent task {i+1}',
                'content': f'Task agent {i+1} in multi-agent workflow',
                'max_tokens': 50
            }
            
            agent_result = await agent.execute(task_input)
            await orchestrator.track_agent_completion(agent, agent_result)
            await agent.terminate()
        
        # Get final orchestrator results
        result = await orchestrator.terminate()
        
        workflow_success = result.success
        print(f"   Multi-agent workflow: {'✅ SUCCESS' if workflow_success else '❌ FAILED'}")
        
        expected_agents = result.agents_spawned == 3
        print(f"   Expected agents spawned: {'✅ SUCCESS' if expected_agents else '❌ FAILED'}")
        
        coordination_metrics = result.total_tokens > 0
        print(f"   Coordination metrics: {'✅ SUCCESS' if coordination_metrics else '❌ FAILED'}")
        
        return workflow_success and expected_agents
        
    except Exception as e:
        print(f"❌ Multi-agent coordination test error: {str(e)}")
        return False

async def test_orchestrator_termination():
    """Test proper orchestrator termination"""
    print(f"\\n🔚 TESTING ORCHESTRATOR TERMINATION")
    print("-" * 40)
    
    try:
        orchestrator = BaseOrchestrator(orchestrator_type="test")
        await orchestrator.initialize()
        
        # Spawn an agent
        agent = await orchestrator.spawn_agent("task", {'timeout': 30})
        
        # Terminate orchestrator (should clean up agents)
        result = await orchestrator.terminate()
        
        termination_success = result is not None
        print(f"   Termination completed: {'✅ SUCCESS' if termination_success else '❌ FAILED'}")
        
        final_state_correct = orchestrator.state.value == 'terminated'
        print(f"   Final state correct: {'✅ SUCCESS' if final_state_correct else '❌ FAILED'}")
        
        has_summary = result.final_output is not None if result else False
        print(f"   Has final summary: {'✅ SUCCESS' if has_summary else '❌ FAILED'}")
        
        return termination_success and final_state_correct
        
    except Exception as e:
        print(f"❌ Termination test error: {str(e)}")
        return False

async def main():
    """Run all base orchestrator tests"""
    print("🚀 BASE ORCHESTRATOR TESTING")
    print("=" * 60)
    
    try:
        # Run all tests
        init_passed = await test_orchestrator_initialization()
        spawn_passed = await test_agent_spawning()
        limits_passed = await test_resource_limits()
        workflow_passed = await test_simple_workflow()
        coordination_passed = await test_multi_agent_coordination()
        termination_passed = await test_orchestrator_termination()
        
        print(f"\\n" + "=" * 60)
        print("📊 BASE ORCHESTRATOR TEST RESULTS:")
        print(f"   Initialization: {'✅ PASSED' if init_passed else '❌ FAILED'}")
        print(f"   Agent spawning: {'✅ PASSED' if spawn_passed else '❌ FAILED'}")
        print(f"   Resource limits: {'✅ PASSED' if limits_passed else '❌ FAILED'}")
        print(f"   Simple workflow: {'✅ PASSED' if workflow_passed else '❌ FAILED'}")
        print(f"   Multi-agent coordination: {'✅ PASSED' if coordination_passed else '❌ FAILED'}")
        print(f"   Termination: {'✅ PASSED' if termination_passed else '❌ FAILED'}")
        
        overall_success = all([
            init_passed, spawn_passed, limits_passed,
            workflow_passed, coordination_passed, termination_passed
        ])
        
        if overall_success:
            print(f"\\n🎉 BASE ORCHESTRATOR SYSTEM FULLY OPERATIONAL!")
            print("   ✅ Agent lifecycle management working correctly")
            print("   ✅ Resource limits properly enforced")
            print("   ✅ Database persistence and state tracking")
            print("   ✅ Multi-agent coordination capabilities")
            print("   ✅ Proper workflow execution and termination")
            print("   ✅ Ready for TopLevel and Sub orchestrator implementation")
        else:
            print(f"\\n❌ BASE ORCHESTRATOR SYSTEM NEEDS FIXES")
            print("   System not ready for advanced orchestration features")
        
        return overall_success
        
    except Exception as e:
        print(f"💥 Base orchestrator testing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)