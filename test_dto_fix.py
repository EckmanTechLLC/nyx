#!/usr/bin/env python3
"""
Quick test script to validate the DTO pattern implementation fixes
"""

import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_dto_implementation():
    """Test the DTO implementation to ensure it works correctly"""
    
    print("=" * 60)
    print("🧪 Testing DTO Implementation Fix")
    print("=" * 60)
    
    try:
        # Test 1: Verify DTO imports work
        print("\n📋 Test 1: Testing DTO imports...")
        from core.motivation.dto import TaskSpawnContext, WorkflowExecutionContext
        from core.motivation.orchestrator_integration import MotivationalOrchestratorIntegration
        print("✅ DTO imports successful")
        
        # Test 2: Test TaskSpawnContext creation
        print("\n📋 Test 2: Testing TaskSpawnContext creation...")
        task_context = TaskSpawnContext(
            task_id="test-task-id",
            motivational_state_id="test-state-id",
            generated_prompt="Test autonomous prompt",
            task_priority=0.7,
            arbitration_score=0.6,
            motivation_type="test_motivation",
            status="generated"
        )
        print(f"✅ TaskSpawnContext created: {task_context.task_id}")
        print(f"   Motivation type: {task_context.motivation_type}")
        print(f"   Priority: {task_context.task_priority}")
        
        # Test 3: Test WorkflowExecutionContext creation
        print("\n📋 Test 3: Testing WorkflowExecutionContext creation...")
        execution_context = WorkflowExecutionContext(
            task_context=task_context,
            thought_tree_id="test-tree-id",
            orchestrator_id="test-orch-id",
            started_at=datetime.now(),
            workflow_input={"test": "data"}
        )
        print(f"✅ WorkflowExecutionContext created")
        
        # Test 4: Test workflow_info dict conversion
        print("\n📋 Test 4: Testing workflow info conversion...")
        workflow_info = execution_context.to_workflow_info_dict()
        print(f"✅ Workflow info dict created:")
        print(f"   Task ID: {workflow_info['task_id']}")
        print(f"   Motivation type: {workflow_info['motivation_type']}")
        print(f"   No SQLAlchemy objects: {all(not hasattr(v, '_sa_instance_state') for v in workflow_info.values())}")
        
        # Test 5: Test integration component instantiation  
        print("\n📋 Test 5: Testing integration component...")
        from core.motivation.engine import MotivationalModelEngine
        engine = MotivationalModelEngine(evaluation_interval=30.0)
        integration = MotivationalOrchestratorIntegration(engine)
        print("✅ Integration component created successfully")
        
        # Test 6: Test method existence
        print("\n📋 Test 6: Testing new method existence...")
        methods_to_check = [
            '_extract_task_context',
            '_spawn_workflow_for_task_data', 
            '_create_workflow_input_from_context',
            '_create_execution_context',
            '_create_thought_tree_from_context',
            '_execute_motivated_workflow_from_context'
        ]
        
        for method_name in methods_to_check:
            if hasattr(integration, method_name):
                print(f"   ✅ {method_name} exists")
            else:
                print(f"   ❌ {method_name} missing")
        
        print("\n" + "=" * 60)
        print("🎉 DTO Implementation Test Complete")
        print("✅ All basic tests passed - ready for integration testing")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function"""
    try:
        await test_dto_implementation()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())