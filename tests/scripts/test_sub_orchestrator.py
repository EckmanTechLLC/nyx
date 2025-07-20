#!/usr/bin/env python3
"""
Test SubOrchestrator Implementation
Tests recursive task decomposition, hierarchical coordination, and
integration with TopLevelOrchestrator following NYX development rules.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.orchestrator.sub import SubOrchestrator, DecompositionStrategy, SubtaskDefinition
from core.orchestrator.top_level import (
    TopLevelOrchestrator, 
    WorkflowInput, 
    WorkflowInputType,
)

async def test_suborchestrator_initialization():
    """Test SubOrchestrator initialization and validation"""
    print("🔧 TESTING SUBORCHESTRATOR INITIALIZATION")
    print("-" * 50)
    
    try:
        # Create real parent orchestrator first
        from core.orchestrator.top_level import TopLevelOrchestrator
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
        from core.orchestrator.top_level import TopLevelOrchestrator
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
        decomposition_task = {
            'title': 'Sequential Task Chain',
            'description': 'Execute tasks that build upon each other in sequence',
            'thought_tree_id': 'c3d4e5f6-7890-1234-5678-90123456def0'
        }
        
        sub_orchestrator = SubOrchestrator(
            parent_orchestrator_id='34567890-3456-3456-3456-34567890abcd',
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
        
        # Verify agents were spawned
        agents_spawned = result.agents_spawned > 0
        print(f"   Agents spawned for subtasks: {'✅ SUCCESS' if agents_spawned else '❌ FAILED'}")
        
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
        
        return execution_success and agents_spawned and has_final_output and has_metadata
        
    except Exception as e:
        print(f"❌ Sequential subtask execution test error: {str(e)}")
        return False

async def test_parallel_subtask_execution():
    """Test parallel subtask execution"""
    print(f"\n⚡ TESTING PARALLEL SUBTASK EXECUTION")
    print("-" * 50)
    
    try:
        decomposition_task = {
            'title': 'Parallel Analysis Tasks',
            'description': 'Multiple independent analysis tasks that can run simultaneously',
            'thought_tree_id': 'd4e5f678-9012-3456-7890-12345678def0'
        }
        
        sub_orchestrator = SubOrchestrator(
            parent_orchestrator_id='45678901-4567-4567-4567-45678901bcde',
            decomposition_task=decomposition_task,
            max_depth=2,
            max_subtasks=4
        )
        
        await sub_orchestrator.initialize()
        
        # Force parallel strategy by creating subtasks without dependencies
        sub_orchestrator.decomposition_plan = sub_orchestrator._create_fallback_decomposition_plan()
        
        # Add multiple subtasks to trigger parallel execution
        for i in range(3):
            subtask = SubtaskDefinition(
                subtask_id=f'parallel-task-{i}',
                title=f'Parallel Task {i+1}',
                description=f'Independent task {i+1} for parallel execution',
                estimated_complexity='medium'
            )
            sub_orchestrator.decomposition_plan.subtasks.append(subtask)
            sub_orchestrator.decomposition_plan.execution_order.append(subtask.subtask_id)
        
        sub_orchestrator.decomposition_plan.strategy = DecompositionStrategy.PARALLEL_BREAKDOWN
        
        # Execute parallel subtasks
        parallel_results = await sub_orchestrator._execute_parallel_subtasks()
        
        # Verify parallel execution
        parallel_executed = parallel_results is not None
        print(f"   Parallel execution completed: {'✅ SUCCESS' if parallel_executed else '❌ FAILED'}")
        
        # Verify multiple results
        multiple_results = parallel_executed and len(parallel_results) > 1
        print(f"   Multiple subtasks executed: {'✅ SUCCESS' if multiple_results else '❌ FAILED'}")
        
        # Verify concurrent execution tracking
        concurrent_tracking = len(sub_orchestrator.spawned_agents) >= 3
        print(f"   Concurrent agent tracking: {'✅ SUCCESS' if concurrent_tracking else '❌ FAILED'}")
        
        # Test full execution
        full_result = await sub_orchestrator.execute_decomposition()
        full_success = full_result.success
        print(f"   Full parallel execution: {'✅ SUCCESS' if full_success else '❌ FAILED'}")
        
        await sub_orchestrator.terminate()
        
        return parallel_executed and multiple_results and full_success
        
    except Exception as e:
        print(f"❌ Parallel subtask execution test error: {str(e)}")
        return False

async def test_result_synthesis():
    """Test result synthesis from subtasks"""
    print(f"\n🔄 TESTING RESULT SYNTHESIS")
    print("-" * 50)
    
    try:
        decomposition_task = {
            'title': 'Synthesis Test Task',
            'description': 'Task to test result aggregation and synthesis',
            'thought_tree_id': 'e5f67890-1234-5678-9012-345678901def'
        }
        
        sub_orchestrator = SubOrchestrator(
            parent_orchestrator_id='56789012-5678-5678-5678-567890123456',
            decomposition_task=decomposition_task,
            max_depth=2,
            max_subtasks=2
        )
        
        await sub_orchestrator.initialize()
        
        # Create mock subtask results for synthesis testing
        from core.agents.base import AgentResult
        mock_results = {
            'subtask-1': AgentResult(
                success=True,
                content='Analysis of system performance shows 85% efficiency'
            ),
            'subtask-2': AgentResult(
                success=True,
                content='Bottleneck identification reveals database query optimization needed'
            )
        }
        
        # Test synthesis
        synthesis_result = await sub_orchestrator._synthesize_subtask_results(mock_results)
        
        # Verify synthesis completed
        synthesis_success = synthesis_result is not None
        print(f"   Synthesis completed: {'✅ SUCCESS' if synthesis_success else '❌ FAILED'}")
        
        # Verify synthesis has content
        has_content = synthesis_success and 'content' in synthesis_result
        print(f"   Synthesized content exists: {'✅ SUCCESS' if has_content else '❌ FAILED'}")
        
        # Verify success flag
        synthesis_marked_success = synthesis_success and synthesis_result.get('success', False)
        print(f"   Synthesis success tracked: {'✅ SUCCESS' if synthesis_marked_success else '❌ FAILED'}")
        
        # Verify synthesis method tracked
        has_method = synthesis_success and 'synthesis_method' in synthesis_result
        print(f"   Synthesis method tracked: {'✅ SUCCESS' if has_method else '❌ FAILED'}")
        
        # Test fallback synthesis
        fallback_result = sub_orchestrator._create_fallback_synthesis(mock_results)
        fallback_works = fallback_result is not None and 'content' in fallback_result
        print(f"   Fallback synthesis works: {'✅ SUCCESS' if fallback_works else '❌ FAILED'}")
        
        await sub_orchestrator.terminate()
        
        return synthesis_success and has_content and synthesis_marked_success and fallback_works
        
    except Exception as e:
        print(f"❌ Result synthesis test error: {str(e)}")
        return False

async def test_integration_with_toplevel():
    """Test SubOrchestrator integration with TopLevelOrchestrator"""
    print(f"\n🔗 TESTING TOPLEVEL ORCHESTRATOR INTEGRATION")
    print("-" * 50)
    
    try:
        # Create TopLevelOrchestrator
        top_level = TopLevelOrchestrator(
            max_concurrent_agents=8,
            max_execution_time_minutes=30,
            max_cost_usd=25.0
        )
        
        await top_level.initialize()
        
        # Create goal workflow that should trigger recursive decomposition
        workflow_input = WorkflowInput(
            input_type=WorkflowInputType.GOAL_WORKFLOW,
            content={
                'goal': {
                    'objective': 'Comprehensive system optimization analysis',
                    'success_criteria': [
                        'identify top 5 performance bottlenecks',
                        'propose specific optimization strategies',
                        'create implementation timeline',
                        'estimate resource requirements'
                    ],
                    'timeline': '1 week'
                }
            },
            priority='high',
            urgency='medium'
        )
        
        # Execute workflow - should use SubOrchestrator
        result = await top_level.execute_workflow(workflow_input)
        
        # Verify workflow completed
        workflow_success = result.success
        print(f"   TopLevel workflow completed: {'✅ SUCCESS' if workflow_success else '❌ FAILED'}")
        
        # Verify recursive decomposition was used
        strategy_used = result.metadata.get('strategy_used', '')
        used_recursive = strategy_used == 'recursive_decomposition'
        print(f"   Recursive decomposition used: {'✅ SUCCESS' if used_recursive else '❌ FAILED'}")
        
        # Verify agents were spawned (indicates SubOrchestrator worked)
        agents_spawned = result.agents_spawned > 0
        print(f"   SubOrchestrator agents spawned: {'✅ SUCCESS' if agents_spawned else '❌ FAILED'}")
        
        # Verify final output exists
        has_final_output = result.final_output is not None
        print(f"   Final output generated: {'✅ SUCCESS' if has_final_output else '❌ FAILED'}")
        
        # Verify cost tracking
        cost_tracked = result.total_cost_usd >= 0
        print(f"   Cost tracking integrated: {'✅ SUCCESS' if cost_tracked else '❌ FAILED'}")
        
        await top_level.terminate()
        
        return workflow_success and used_recursive and agents_spawned and has_final_output
        
    except Exception as e:
        print(f"❌ TopLevel integration test error: {str(e)}")
        return False

async def test_depth_and_resource_limits():
    """Test depth limiting and resource constraint inheritance"""
    print(f"\n🛡️ TESTING DEPTH & RESOURCE LIMITS")
    print("-" * 50)
    
    try:
        decomposition_task = {
            'title': 'Depth Limit Test',
            'description': 'Test depth limiting behavior',
            'thought_tree_id': 'f6789012-3456-7890-1234-56789012345f'
        }
        
        # Test depth limit validation
        sub_orchestrator = SubOrchestrator(
            parent_orchestrator_id='67890123-6789-6789-6789-67890123456f',
            decomposition_task=decomposition_task,
            max_depth=1,  # Very shallow depth
            max_subtasks=2
        )
        
        # Set current depth to max depth to test limit
        sub_orchestrator.current_depth = 1
        
        # Initialize should fail due to depth limit
        init_with_depth_limit = await sub_orchestrator.initialize()
        depth_limit_enforced = not init_with_depth_limit
        print(f"   Depth limit enforced: {'✅ SUCCESS' if depth_limit_enforced else '❌ FAILED'}")
        
        # Test resource inheritance
        inherit_context = {
            'resource_constraints': {
                'max_concurrent_agents': 3,
                'max_cost_remaining': 15.0
            },
            'quality_settings': {
                'validation_level': 'strict'
            }
        }
        
        sub_orchestrator2 = SubOrchestrator(
            parent_orchestrator_id='78901234-7890-7890-7890-78901234567f',
            decomposition_task=decomposition_task,
            max_depth=3,
            max_concurrent_agents=5,  # Should be limited by inherited constraints
            inherit_context=inherit_context
        )
        
        await sub_orchestrator2.initialize()
        
        # Verify resource inheritance
        resource_inherited = hasattr(sub_orchestrator2, 'inherited_constraints')
        print(f"   Resource inheritance setup: {'✅ SUCCESS' if resource_inherited else '❌ FAILED'}")
        
        # Verify constraint limits
        inherited_limits = sub_orchestrator2.inherited_constraints.get('max_concurrent_agents', 0)
        constraint_applied = inherited_limits == 3
        print(f"   Resource constraints applied: {'✅ SUCCESS' if constraint_applied else '❌ FAILED'}")
        
        # Verify quality settings inheritance
        quality_inherited = hasattr(sub_orchestrator2, 'inherited_quality_settings')
        print(f"   Quality settings inherited: {'✅ SUCCESS' if quality_inherited else '❌ FAILED'}")
        
        await sub_orchestrator2.terminate()
        
        return depth_limit_enforced and resource_inherited and constraint_applied and quality_inherited
        
    except Exception as e:
        print(f"❌ Depth and resource limits test error: {str(e)}")
        return False

async def test_error_handling_and_fallbacks():
    """Test error handling and fallback mechanisms"""
    print(f"\n🚨 TESTING ERROR HANDLING & FALLBACKS")
    print("-" * 50)
    
    try:
        # Test with invalid decomposition task
        invalid_task = {
            'title': 'Invalid Task',
            # Missing required fields intentionally
        }
        
        sub_orchestrator = SubOrchestrator(
            parent_orchestrator_id='89012345-8901-8901-8901-89012345678f',
            decomposition_task=invalid_task,
            max_depth=2
        )
        
        # Initialize should fail gracefully
        init_with_invalid_task = await sub_orchestrator.initialize()
        graceful_failure = not init_with_invalid_task
        print(f"   Invalid task handled gracefully: {'✅ SUCCESS' if graceful_failure else '❌ FAILED'}")
        
        # Test fallback decomposition plan
        valid_task = {
            'title': 'Fallback Test Task',
            'description': 'Test fallback mechanisms',
            'thought_tree_id': '90123456-9012-9012-9012-90123456789f'
        }
        
        sub_orchestrator2 = SubOrchestrator(
            parent_orchestrator_id='01234567-0123-0123-0123-01234567890f',
            decomposition_task=valid_task,
            max_depth=2
        )
        
        await sub_orchestrator2.initialize()
        
        # Test fallback plan creation
        fallback_plan = sub_orchestrator2._create_fallback_decomposition_plan()
        fallback_created = fallback_plan is not None and len(fallback_plan.subtasks) > 0
        print(f"   Fallback plan creation: {'✅ SUCCESS' if fallback_created else '❌ FAILED'}")
        
        # Test error result creation
        error_result = sub_orchestrator2._create_error_result("Test error message")
        error_result_valid = (error_result is not None and 
                             not error_result.success and 
                             error_result.error_message is not None)
        print(f"   Error result creation: {'✅ SUCCESS' if error_result_valid else '❌ FAILED'}")
        
        # Test execution with fallback
        execution_result = await sub_orchestrator2.execute_decomposition()
        execution_completed = execution_result is not None
        print(f"   Execution with fallbacks: {'✅ SUCCESS' if execution_completed else '❌ FAILED'}")
        
        await sub_orchestrator2.terminate()
        
        return graceful_failure and fallback_created and error_result_valid and execution_completed
        
    except Exception as e:
        print(f"❌ Error handling test error: {str(e)}")
        return False

async def main():
    """Run all SubOrchestrator tests"""
    print("🚀 SUB-ORCHESTRATOR TESTING")
    print("=" * 60)
    
    try:
        # Run all comprehensive tests
        initialization_passed = await test_suborchestrator_initialization()
        decomposition_passed = await test_task_decomposition_planning()
        sequential_passed = await test_sequential_subtask_execution()
        parallel_passed = await test_parallel_subtask_execution()
        synthesis_passed = await test_result_synthesis()
        integration_passed = await test_integration_with_toplevel()
        limits_passed = await test_depth_and_resource_limits()
        error_handling_passed = await test_error_handling_and_fallbacks()
        
        print(f"\n" + "=" * 60)
        print("📊 SUB-ORCHESTRATOR TEST RESULTS:")
        print(f"   SubOrchestrator initialization: {'✅ PASSED' if initialization_passed else '❌ FAILED'}")
        print(f"   Task decomposition planning: {'✅ PASSED' if decomposition_passed else '❌ FAILED'}")
        print(f"   Sequential subtask execution: {'✅ PASSED' if sequential_passed else '❌ FAILED'}")
        print(f"   Parallel subtask execution: {'✅ PASSED' if parallel_passed else '❌ FAILED'}")
        print(f"   Result synthesis: {'✅ PASSED' if synthesis_passed else '❌ FAILED'}")
        print(f"   TopLevel integration: {'✅ PASSED' if integration_passed else '❌ FAILED'}")
        print(f"   Depth & resource limits: {'✅ PASSED' if limits_passed else '❌ FAILED'}")
        print(f"   Error handling & fallbacks: {'✅ PASSED' if error_handling_passed else '❌ FAILED'}")
        
        overall_success = all([
            initialization_passed, decomposition_passed, sequential_passed, parallel_passed,
            synthesis_passed, integration_passed, limits_passed, error_handling_passed
        ])
        
        if overall_success:
            print(f"\n🎉 SUB-ORCHESTRATOR SYSTEM FULLY OPERATIONAL!")
            print("   ✅ Recursive task decomposition working")
            print("   ✅ Hierarchical coordination operational")
            print("   ✅ Parent-child resource inheritance")
            print("   ✅ Multiple execution strategies supported")
            print("   ✅ Result synthesis and aggregation")
            print("   ✅ Integration with TopLevelOrchestrator")
            print("   ✅ Robust error handling and fallbacks")
            print("   ✅ Ready for production recursive orchestration")
        else:
            print(f"\n❌ SUB-ORCHESTRATOR SYSTEM NEEDS FIXES")
            print("   System not ready for production deployment")
        
        return overall_success
        
    except Exception as e:
        print(f"💥 Sub-orchestrator testing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)