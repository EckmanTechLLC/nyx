#!/usr/bin/env python3
"""
Test SubOrchestrator Basic Functionality
Tests initialization, decomposition planning, and sequential execution.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.orchestrator.sub import SubOrchestrator, DecompositionStrategy, SubtaskDefinition
from core.orchestrator.top_level import TopLevelOrchestrator

async def test_suborchestrator_initialization():
    """Test SubOrchestrator initialization and validation"""
    print("🔧 TESTING SUBORCHESTRATOR INITIALIZATION")
    print("-" * 50)
    
    try:
        # Create real parent orchestrator first
        parent_orchestrator = TopLevelOrchestrator(max_concurrent_agents=5)
        await parent_orchestrator.initialize()
        
        # Test valid initialization with real parent
        decomposition_task = {
            'title': 'Test Task Decomposition',
            'description': 'Break down a complex task into manageable subtasks',
            'thought_tree_id': parent_orchestrator.thought_tree_id
        }
        
        sub_orchestrator = SubOrchestrator(
            parent_orchestrator_id=parent_orchestrator.id,
            decomposition_task=decomposition_task,
            max_depth=2,
            max_subtasks=4
        )
        
        # Test initialization
        initialization_success = await sub_orchestrator.initialize()
        print(f"   Valid initialization: {'✅ SUCCESS' if initialization_success else '❌ FAILED'}")
        
        # Test state after initialization
        correct_state = sub_orchestrator.state.value == 'active'
        print(f"   Correct state (active): {'✅ SUCCESS' if correct_state else '❌ FAILED'}")
        
        # Test depth validation
        has_depth_tracking = hasattr(sub_orchestrator, 'current_depth')
        print(f"   Depth tracking: {'✅ SUCCESS' if has_depth_tracking else '❌ FAILED'}")
        
        # Test parent coordination setup
        has_parent_id = sub_orchestrator.parent_orchestrator_id is not None
        print(f"   Parent orchestrator linkage: {'✅ SUCCESS' if has_parent_id else '❌ FAILED'}")
        
        await sub_orchestrator.terminate()
        await parent_orchestrator.terminate()
        
        return initialization_success and correct_state and has_depth_tracking and has_parent_id
        
    except Exception as e:
        print(f"❌ SubOrchestrator initialization test error: {str(e)}")
        return False

async def test_task_decomposition_planning():
    """Test task analysis and decomposition planning"""
    print(f"\n📋 TESTING TASK DECOMPOSITION PLANNING")
    print("-" * 50)
    
    try:
        # Create real parent orchestrator
        parent_orchestrator = TopLevelOrchestrator(max_concurrent_agents=8)
        await parent_orchestrator.initialize()
        
        decomposition_task = {
            'title': 'Multi-step Analysis Project',
            'description': 'Analyze system performance, identify bottlenecks, and propose optimizations with implementation plan',
            'thought_tree_id': parent_orchestrator.thought_tree_id
        }
        
        sub_orchestrator = SubOrchestrator(
            parent_orchestrator_id=parent_orchestrator.id,
            decomposition_task=decomposition_task,
            max_depth=2,
            max_subtasks=5
        )
        
        await sub_orchestrator.initialize()
        
        # Test decomposition planning (calls _analyze_and_plan_decomposition internally)
        decomposition_plan = await sub_orchestrator._analyze_and_plan_decomposition()
        
        # Verify plan creation
        plan_created = decomposition_plan is not None
        print(f"   Decomposition plan created: {'✅ SUCCESS' if plan_created else '❌ FAILED'}")
        
        # Verify plan has subtasks
        has_subtasks = plan_created and len(decomposition_plan.subtasks) > 0
        print(f"   Plan contains subtasks: {'✅ SUCCESS' if has_subtasks else '❌ FAILED'}")
        
        # Verify execution order
        has_execution_order = plan_created and len(decomposition_plan.execution_order) > 0
        print(f"   Execution order defined: {'✅ SUCCESS' if has_execution_order else '❌ FAILED'}")
        
        # Verify strategy selection
        has_strategy = plan_created and decomposition_plan.strategy in DecompositionStrategy
        print(f"   Strategy selected: {'✅ SUCCESS' if has_strategy else '❌ FAILED'}")
        
        # Verify subtask limit respected
        within_limits = not has_subtasks or len(decomposition_plan.subtasks) <= sub_orchestrator.max_subtasks
        print(f"   Subtask limits respected: {'✅ SUCCESS' if within_limits else '❌ FAILED'}")
        
        await sub_orchestrator.terminate()
        await parent_orchestrator.terminate()
        
        return plan_created and has_subtasks and has_execution_order and has_strategy and within_limits
        
    except Exception as e:
        print(f"❌ Task decomposition planning test error: {str(e)}")
        return False

async def test_sequential_subtask_execution():
    """Test sequential subtask execution"""
    print(f"\n⏭️ TESTING SEQUENTIAL SUBTASK EXECUTION")
    print("-" * 50)
    
    try:
        # Create real parent orchestrator
        parent_orchestrator = TopLevelOrchestrator(max_concurrent_agents=8)
        await parent_orchestrator.initialize()
        
        decomposition_task = {
            'title': 'Sequential Task Chain',
            'description': 'Execute tasks that build upon each other in sequence',
            'thought_tree_id': parent_orchestrator.thought_tree_id
        }
        
        sub_orchestrator = SubOrchestrator(
            parent_orchestrator_id=parent_orchestrator.id,
            decomposition_task=decomposition_task,
            max_depth=2,
            max_subtasks=3
        )
        
        await sub_orchestrator.initialize()
        
        # Execute full decomposition to test sequential execution
        result = await sub_orchestrator.execute_decomposition()
        
        # Verify execution completed
        execution_success = result.success
        print(f"   Sequential execution completed: {'✅ SUCCESS' if execution_success else '❌ FAILED'}")
        
        # Verify agents were spawned and processed
        agents_processed = result.agents_completed + result.agents_failed > 0
        print(f"   Agents spawned for subtasks: {'✅ SUCCESS' if agents_processed else '❌ FAILED'}")
        
        # Verify final output exists
        has_final_output = result.final_output is not None
        print(f"   Final output synthesized: {'✅ SUCCESS' if has_final_output else '❌ FAILED'}")
        
        # Verify metadata tracking
        has_metadata = 'decomposition_strategy' in result.metadata
        print(f"   Strategy metadata tracked: {'✅ SUCCESS' if has_metadata else '❌ FAILED'}")
        
        # Verify depth tracking
        correct_depth = result.metadata.get('depth', -1) == 0  # SubOrchestrator starts at depth 0 for this test
        print(f"   Depth tracking accurate: {'✅ SUCCESS' if correct_depth else '❌ FAILED'}")
        
        await sub_orchestrator.terminate()
        await parent_orchestrator.terminate()
        
        return execution_success and agents_processed and has_final_output and has_metadata
        
    except Exception as e:
        print(f"❌ Sequential subtask execution test error: {str(e)}")
        return False

async def main():
    """Run basic SubOrchestrator tests"""
    print("🚀 SUB-ORCHESTRATOR BASIC TESTING")
    print("=" * 60)
    
    try:
        # Run basic tests
        initialization_passed = await test_suborchestrator_initialization()
        decomposition_passed = await test_task_decomposition_planning()
        sequential_passed = await test_sequential_subtask_execution()
        
        print(f"\n" + "=" * 60)
        print("📊 SUB-ORCHESTRATOR BASIC TEST RESULTS:")
        print(f"   SubOrchestrator initialization: {'✅ PASSED' if initialization_passed else '❌ FAILED'}")
        print(f"   Task decomposition planning: {'✅ PASSED' if decomposition_passed else '❌ FAILED'}")
        print(f"   Sequential subtask execution: {'✅ PASSED' if sequential_passed else '❌ FAILED'}")
        
        overall_success = all([initialization_passed, decomposition_passed, sequential_passed])
        
        if overall_success:
            print(f"\n🎉 SUB-ORCHESTRATOR BASIC FUNCTIONALITY OPERATIONAL!")
            print("   ✅ Initialization and validation working")
            print("   ✅ Task decomposition planning functional")
            print("   ✅ Sequential execution with real agents")
            print("   ✅ Ready for advanced functionality testing")
        else:
            print(f"\n❌ SUB-ORCHESTRATOR BASIC TESTS NEED FIXES")
            print("   Core functionality not ready")
        
        return overall_success
        
    except Exception as e:
        print(f"💥 Sub-orchestrator basic testing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)