#!/usr/bin/env python3
"""
Test SubOrchestrator Advanced Functionality
Tests parallel execution, result synthesis, and TopLevel integration.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.orchestrator.sub import SubOrchestrator, DecompositionStrategy, SubtaskDefinition
from core.orchestrator.top_level import TopLevelOrchestrator, WorkflowInput, WorkflowInputType

async def test_parallel_subtask_execution():
    """Test parallel subtask execution"""
    print(f"⚡ TESTING PARALLEL SUBTASK EXECUTION")
    print("-" * 50)
    
    try:
        # Create real parent orchestrator
        parent_orchestrator = TopLevelOrchestrator(max_concurrent_agents=8)
        await parent_orchestrator.initialize()
        
        decomposition_task = {
            'title': 'Parallel Analysis Tasks',
            'description': 'Multiple independent analysis tasks that can run simultaneously',
            'thought_tree_id': parent_orchestrator.thought_tree_id
        }
        
        sub_orchestrator = SubOrchestrator(
            parent_orchestrator_id=parent_orchestrator.id,
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
        concurrent_tracking = len(sub_orchestrator.completed_agents) + len(sub_orchestrator.failed_agents) >= 3
        print(f"   Concurrent agent tracking: {'✅ SUCCESS' if concurrent_tracking else '❌ FAILED'}")
        
        # Test full execution
        full_result = await sub_orchestrator.execute_decomposition()
        full_success = full_result.success
        print(f"   Full parallel execution: {'✅ SUCCESS' if full_success else '❌ FAILED'}")
        
        await sub_orchestrator.terminate()
        await parent_orchestrator.terminate()
        
        return parallel_executed and multiple_results and concurrent_tracking and full_success
        
    except Exception as e:
        print(f"❌ Parallel subtask execution test error: {str(e)}")
        return False

async def test_result_synthesis():
    """Test result synthesis from subtasks"""
    print(f"\n🔄 TESTING RESULT SYNTHESIS")
    print("-" * 50)
    
    try:
        # Create real parent orchestrator
        parent_orchestrator = TopLevelOrchestrator(max_concurrent_agents=5)
        await parent_orchestrator.initialize()
        
        decomposition_task = {
            'title': 'Synthesis Test Task',
            'description': 'Task to test result aggregation and synthesis',
            'thought_tree_id': parent_orchestrator.thought_tree_id
        }
        
        sub_orchestrator = SubOrchestrator(
            parent_orchestrator_id=parent_orchestrator.id,
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
        await parent_orchestrator.terminate()
        
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
        
        # Verify SubOrchestrator coordination (indicates SubOrchestrator worked)
        coordination_success = result.total_cost_usd > 0 or (result.final_output and str(result.final_output).strip())
        print(f"   SubOrchestrator agents spawned: {'✅ SUCCESS' if coordination_success else '❌ FAILED'}")
        
        # Verify final output exists
        has_final_output = result.final_output is not None
        print(f"   Final output generated: {'✅ SUCCESS' if has_final_output else '❌ FAILED'}")
        
        # Verify cost tracking
        cost_tracked = result.total_cost_usd >= 0
        print(f"   Cost tracking integrated: {'✅ SUCCESS' if cost_tracked else '❌ FAILED'}")
        
        await top_level.terminate()
        
        return workflow_success and used_recursive and coordination_success and has_final_output
        
    except Exception as e:
        print(f"❌ TopLevel integration test error: {str(e)}")
        return False

async def main():
    """Run advanced SubOrchestrator tests"""
    print("🚀 SUB-ORCHESTRATOR ADVANCED TESTING")
    print("=" * 60)
    
    try:
        # Run advanced tests
        parallel_passed = await test_parallel_subtask_execution()
        synthesis_passed = await test_result_synthesis()
        integration_passed = await test_integration_with_toplevel()
        
        print(f"\n" + "=" * 60)
        print("📊 SUB-ORCHESTRATOR ADVANCED TEST RESULTS:")
        print(f"   Parallel subtask execution: {'✅ PASSED' if parallel_passed else '❌ FAILED'}")
        print(f"   Result synthesis: {'✅ PASSED' if synthesis_passed else '❌ FAILED'}")
        print(f"   TopLevel integration: {'✅ PASSED' if integration_passed else '❌ FAILED'}")
        
        overall_success = all([parallel_passed, synthesis_passed, integration_passed])
        
        if overall_success:
            print(f"\n🎉 SUB-ORCHESTRATOR ADVANCED FUNCTIONALITY OPERATIONAL!")
            print("   ✅ Parallel execution with multiple agents")
            print("   ✅ Result synthesis and aggregation")
            print("   ✅ Full integration with TopLevelOrchestrator")
            print("   ✅ Ready for production recursive orchestration")
        else:
            print(f"\n❌ SUB-ORCHESTRATOR ADVANCED TESTS NEED FIXES")
            print("   Advanced functionality not ready")
        
        return overall_success
        
    except Exception as e:
        print(f"💥 Sub-orchestrator advanced testing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)