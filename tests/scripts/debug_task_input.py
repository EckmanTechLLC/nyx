#!/usr/bin/env python3
"""
Debug what inputs are being passed to TaskAgent
"""
import asyncio
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set up logging to capture failures
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from core.orchestrator.top_level import (
    TopLevelOrchestrator, 
    WorkflowInput, 
    WorkflowInputType
)

async def debug_task_input():
    """Debug task input generation"""
    print("🔍 DEBUGGING TASK INPUT GENERATION")
    print("-" * 50)
    
    try:
        orchestrator = TopLevelOrchestrator(
            max_concurrent_agents=8,
            max_execution_time_minutes=45,
            max_cost_usd=40.0
        )
        
        await orchestrator.initialize()
        
        # Create structured task input
        workflow_input = WorkflowInput(
            input_type=WorkflowInputType.STRUCTURED_TASK,
            content={
                'task_definition': {
                    'primary_objective': 'Generate comprehensive API documentation',
                    'constraints': [
                        'must include authentication examples',
                        'must follow OpenAPI 3.0 specification'
                    ],
                    'deliverables': [
                        'API specification file',
                        'integration guide'
                    ]
                }
            }
        )
        
        print(f"Original Workflow Input:")
        print(f"  Type: {workflow_input.input_type.value}")
        print(f"  Content: {workflow_input.content}")
        
        # Test task decomposition step by step
        print(f"\n1️⃣ TESTING _convert_to_task_input:")
        task_input = await orchestrator._convert_to_task_input(workflow_input)
        print(f"  Task input: {task_input}")
        
        # Test task decomposition
        print(f"\n2️⃣ TESTING _decompose_to_subtasks:")
        subtasks = await orchestrator._decompose_to_subtasks(workflow_input, max_tasks=3)
        print(f"  Number of subtasks: {len(subtasks)}")
        for i, subtask in enumerate(subtasks):
            print(f"  Subtask {i+1}: {subtask}")
        
        # Test direct TaskAgent execution with one of these inputs
        print(f"\n3️⃣ TESTING DIRECT TASKAGENT EXECUTION:")
        from core.agents.task import TaskAgent
        
        test_agent = TaskAgent(
            thought_tree_id=orchestrator.thought_tree_id,
            parent_agent_id=None
        )
        await test_agent.initialize()
        
        if len(subtasks) > 0:
            test_input = subtasks[0]
            print(f"Testing input: {test_input}")
            
            # Check input validation manually
            validation_result = await test_agent._validate_input(test_input)
            print(f"Input validation result: {validation_result}")
            
            if validation_result:
                # Try to execute
                result = await test_agent.execute(test_input)
                print(f"Execution result:")
                print(f"  Success: {result.success}")
                print(f"  Content length: {len(result.content) if result.content else 0}")
                print(f"  Error: {result.error_message}")
            else:
                print(f"❌ Input validation failed")
                
                # Check what's missing
                required_fields = ['task_type', 'description', 'content']
                for field in required_fields:
                    if field not in test_input:
                        print(f"  Missing field: {field}")
                    else:
                        print(f"  Has field {field}: {test_input[field]}")
        
        await test_agent.terminate()
        await orchestrator.terminate()
        
    except Exception as e:
        print(f"❌ Debug error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_task_input())