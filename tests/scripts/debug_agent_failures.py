#!/usr/bin/env python3
"""
Debug agent execution failures in TopLevelOrchestrator
"""
import asyncio
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set up logging to capture agent failures
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from core.orchestrator.top_level import (
    TopLevelOrchestrator, 
    WorkflowInput, 
    WorkflowInputType,
    WorkflowStrategy,
    ComplexityLevel
)

async def debug_agent_failures():
    """Debug specific agent execution failures"""
    print("🔍 DEBUGGING AGENT EXECUTION FAILURES")
    print("-" * 60)
    
    try:
        orchestrator = TopLevelOrchestrator(
            max_concurrent_agents=8,
            max_execution_time_minutes=45,
            max_cost_usd=40.0
        )
        
        await orchestrator.initialize()
        
        # Create structured task input (same as failing test)
        workflow_input = WorkflowInput(
            input_type=WorkflowInputType.STRUCTURED_TASK,
            content={
                'task_definition': {
                    'primary_objective': 'Generate comprehensive API documentation',
                    'constraints': [
                        'must include authentication examples',
                        'must follow OpenAPI 3.0 specification',
                        'must include error handling patterns'
                    ],
                    'deliverables': [
                        'API specification file',
                        'integration guide', 
                        'code examples',
                        'troubleshooting guide'
                    ],
                    'quality_requirements': {
                        'validation_level': 'strict',
                        'review_required': True
                    }
                }
            },
            execution_context={
                'resource_limits': {
                    'max_concurrent_agents': 6,
                    'max_execution_time_minutes': 40
                },
                'quality_settings': {
                    'validation_level': 'strict',
                    'require_council_consensus': True
                }
            },
            domain_context={
                'project_info': {
                    'name': 'NYX API',
                    'type': 'rest_api',
                    'frameworks': ['fastapi', 'sqlalchemy']
                }
            },
            priority='high',
            urgency='medium'
        )
        
        print(f"Workflow Input: {workflow_input.input_type.value}")
        print(f"Strategy should be: council_driven (due to require_council_consensus=True)")
        
        # Analyze complexity and strategy
        complexity = await orchestrator._analyze_complexity(workflow_input)
        strategy = await orchestrator._select_strategy(workflow_input, complexity)
        
        print(f"Selected strategy: {strategy.value}")
        print(f"Quality requirements: {complexity.quality_requirements.value}")
        
        # Monitor agent spawning and execution
        print("\n🤖 MONITORING AGENT EXECUTION:")
        print("-" * 40)
        
        # Execute workflow with detailed monitoring
        result = await orchestrator.execute_workflow(workflow_input)
        
        print(f"\n📊 EXECUTION RESULTS:")
        print(f"  Overall success: {result.success}")
        print(f"  Agents spawned: {result.agents_spawned}")
        print(f"  Total cost: ${result.total_cost_usd}")
        print(f"  Workflow ID: {result.workflow_id}")
        print(f"  Final output length: {len(result.final_output) if result.final_output else 0}")
        
        print(f"\n📋 DETAILED MONITORING:")
        monitoring = result.metadata.get('monitoring_final_state', {})
        print(f"  Progress: {monitoring.get('progress_percentage', 0)}%")
        print(f"  Agents active: {monitoring.get('agents_active', 0)}")
        print(f"  Agents completed: {monitoring.get('agents_completed', 0)}")
        print(f"  Agents failed: {monitoring.get('agents_failed', 0)}")
        print(f"  Time elapsed: {monitoring.get('time_elapsed_minutes', 0):.1f} minutes")
        
        print(f"\n❗ FAILURE ANALYSIS:")
        if monitoring.get('agents_failed', 0) > 0:
            print(f"  {monitoring['agents_failed']} agents failed out of {result.agents_spawned} total")
            print(f"  Success rate: {(monitoring.get('agents_completed', 0) / result.agents_spawned * 100):.1f}%")
            
            # Check for specific error patterns
            if result.error_message:
                print(f"  Error message: {result.error_message}")
            else:
                print(f"  No error message provided (this is a bug)")
        
        # Check orchestrator state after execution
        print(f"\n🔧 ORCHESTRATOR STATE:")
        status = await orchestrator.get_workflow_status()
        print(f"  Workflow state: {status.get('workflow_state', 'unknown')}")
        print(f"  Current strategy: {status.get('current_strategy', 'none')}")
        
        await orchestrator.terminate()
        
        # Analysis summary
        print(f"\n📈 SUMMARY:")
        agents_failed = monitoring.get('agents_failed', 0)
        if agents_failed > 0:
            print(f"  ❌ {agents_failed} agents failed - this causes workflow.success=False")
            print(f"  🔍 Need to investigate why agents are failing internally")
            print(f"  🔧 Consider implementing partial success handling")
        else:
            print(f"  ✅ All agents succeeded - workflow should be marked successful")
        
        return result.success
        
    except Exception as e:
        print(f"❌ Debug error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_agent_failures())
    print(f"\nDebugging completed. Success: {success}")
    sys.exit(0 if success else 1)