#!/usr/bin/env python3
"""
Test SubOrchestrator Limits and Error Handling
Tests depth limits, resource constraints, and error recovery.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.orchestrator.sub import SubOrchestrator
from core.orchestrator.top_level import TopLevelOrchestrator

async def test_depth_and_resource_limits():
    """Test depth limiting and resource constraint inheritance"""
    print(f"🛡️ TESTING DEPTH & RESOURCE LIMITS")
    print("-" * 50)
    
    try:
        # Create real parent orchestrator
        parent_orchestrator = TopLevelOrchestrator(max_concurrent_agents=5)
        await parent_orchestrator.initialize()
        
        decomposition_task = {
            'title': 'Depth Limit Test',
            'description': 'Test depth limiting behavior',
            'thought_tree_id': parent_orchestrator.thought_tree_id
        }
        
        # Test depth limit validation
        sub_orchestrator = SubOrchestrator(
            parent_orchestrator_id=parent_orchestrator.id,
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
            parent_orchestrator_id=parent_orchestrator.id,
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
        await parent_orchestrator.terminate()
        
        return depth_limit_enforced and resource_inherited and constraint_applied and quality_inherited
        
    except Exception as e:
        print(f"❌ Depth and resource limits test error: {str(e)}")
        return False

async def test_error_handling_and_fallbacks():
    """Test error handling and fallback mechanisms"""
    print(f"\n🚨 TESTING ERROR HANDLING & FALLBACKS")
    print("-" * 50)
    
    try:
        # Create real parent orchestrator
        parent_orchestrator = TopLevelOrchestrator(max_concurrent_agents=5)
        await parent_orchestrator.initialize()
        
        # Test with invalid decomposition task
        invalid_task = {
            'title': 'Invalid Task',
            # Missing required fields intentionally
        }
        
        sub_orchestrator = SubOrchestrator(
            parent_orchestrator_id=parent_orchestrator.id,
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
            'thought_tree_id': parent_orchestrator.thought_tree_id
        }
        
        sub_orchestrator2 = SubOrchestrator(
            parent_orchestrator_id=parent_orchestrator.id,
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
        await parent_orchestrator.terminate()
        
        return graceful_failure and fallback_created and error_result_valid and execution_completed
        
    except Exception as e:
        print(f"❌ Error handling test error: {str(e)}")
        return False

async def test_workflow_status_reporting():
    """Test comprehensive workflow status reporting"""
    print(f"\n📋 TESTING WORKFLOW STATUS REPORTING")
    print("-" * 50)
    
    try:
        # Create real parent orchestrator
        parent_orchestrator = TopLevelOrchestrator(max_concurrent_agents=5)
        await parent_orchestrator.initialize()
        
        decomposition_task = {
            'title': 'Status Test Task',
            'description': 'Task to test status reporting',
            'thought_tree_id': parent_orchestrator.thought_tree_id
        }
        
        sub_orchestrator = SubOrchestrator(
            parent_orchestrator_id=parent_orchestrator.id,
            decomposition_task=decomposition_task,
            max_depth=2,
            max_subtasks=3
        )
        
        await sub_orchestrator.initialize()
        
        # Check initial status  
        initial_status = await sub_orchestrator.get_orchestrator_status()
        
        has_orchestrator_id = 'orchestrator_id' in initial_status
        print(f"   Initial status structure: {'✅ SUCCESS' if has_orchestrator_id else '❌ FAILED'}")
        
        has_type = initial_status.get('orchestrator_type') == 'sub'
        print(f"   Correct orchestrator type: {'✅ SUCCESS' if has_type else '❌ FAILED'}")
        
        has_state = 'state' in initial_status
        print(f"   State tracking: {'✅ SUCCESS' if has_state else '❌ FAILED'}")
        
        # Execute decomposition and check final status
        result = await sub_orchestrator.execute_decomposition()
        
        # Get final status
        final_status = await sub_orchestrator.get_orchestrator_status()
        
        has_agents_info = 'agents_spawned' in final_status
        print(f"   Agent tracking in status: {'✅ SUCCESS' if has_agents_info else '❌ FAILED'}")
        
        has_timestamp = 'updated_at' in final_status
        print(f"   Timestamp tracking: {'✅ SUCCESS' if has_timestamp else '❌ FAILED'}")
        
        await sub_orchestrator.terminate()
        await parent_orchestrator.terminate()
        
        return has_orchestrator_id and has_type and has_state and has_agents_info and has_timestamp
        
    except Exception as e:
        print(f"❌ Workflow status reporting test error: {str(e)}")
        return False

async def main():
    """Run limits and error handling tests"""
    print("🚀 SUB-ORCHESTRATOR LIMITS & ERROR HANDLING TESTING")
    print("=" * 60)
    
    try:
        # Run limits and error handling tests
        limits_passed = await test_depth_and_resource_limits()
        error_handling_passed = await test_error_handling_and_fallbacks()
        status_reporting_passed = await test_workflow_status_reporting()
        
        print(f"\n" + "=" * 60)
        print("📊 SUB-ORCHESTRATOR LIMITS & ERROR HANDLING RESULTS:")
        print(f"   Depth & resource limits: {'✅ PASSED' if limits_passed else '❌ FAILED'}")
        print(f"   Error handling & fallbacks: {'✅ PASSED' if error_handling_passed else '❌ FAILED'}")
        print(f"   Workflow status reporting: {'✅ PASSED' if status_reporting_passed else '❌ FAILED'}")
        
        overall_success = all([limits_passed, error_handling_passed, status_reporting_passed])
        
        if overall_success:
            print(f"\n🎉 SUB-ORCHESTRATOR LIMITS & ERROR HANDLING OPERATIONAL!")
            print("   ✅ Depth and resource constraints enforced")
            print("   ✅ Graceful error handling and fallbacks")
            print("   ✅ Comprehensive status reporting")
            print("   ✅ Ready for production deployment")
        else:
            print(f"\n❌ SUB-ORCHESTRATOR LIMITS & ERROR HANDLING NEED FIXES")
            print("   System not ready for production deployment")
        
        return overall_success
        
    except Exception as e:
        print(f"💥 Sub-orchestrator limits testing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)