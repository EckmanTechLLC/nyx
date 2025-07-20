#!/usr/bin/env python3
"""
Debug specific test failures in TopLevelOrchestrator
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.orchestrator.top_level import (
    TopLevelOrchestrator, 
    WorkflowInput, 
    WorkflowInputType,
    WorkflowStrategy,
    ComplexityLevel
)

async def debug_structured_task_failure():
    """Debug structured task workflow failure"""
    print("🔍 DEBUGGING STRUCTURED TASK WORKFLOW")
    print("-" * 50)
    
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
        
        print(f"Input type: {workflow_input.input_type.value}")
        print(f"Priority: {workflow_input.priority}, Urgency: {workflow_input.urgency}")
        
        # Execute workflow
        result = await orchestrator.execute_workflow(workflow_input)
        
        print(f"\nRESULT ANALYSIS:")
        print(f"  Success: {result.success}")
        print(f"  Agents spawned: {result.agents_spawned}")
        print(f"  Total cost: ${result.total_cost_usd}")
        print(f"  Error message: {result.error_message}")
        print(f"  Final output length: {len(result.final_output) if result.final_output else 0}")
        
        print(f"\nMETADATA:")
        for key, value in result.metadata.items():
            print(f"  {key}: {value}")
        
        await orchestrator.terminate()
        
    except Exception as e:
        print(f"❌ Debug error: {str(e)}")
        import traceback
        traceback.print_exc()

async def debug_goal_workflow_failure():
    """Debug goal-based workflow failure"""
    print("\n🔍 DEBUGGING GOAL-BASED WORKFLOW")
    print("-" * 50)
    
    try:
        orchestrator = TopLevelOrchestrator(
            max_concurrent_agents=10,
            max_execution_time_minutes=60,
            max_cost_usd=50.0
        )
        
        await orchestrator.initialize()
        
        # Create goal-based workflow input
        workflow_input = WorkflowInput(
            input_type=WorkflowInputType.GOAL_WORKFLOW,
            content={
                'goal': {
                    'objective': 'Improve system code quality and maintainability',
                    'success_criteria': [
                        'reduce code complexity metrics by 20%',
                        'increase test coverage to 90%',
                        'eliminate all critical security warnings',
                        'improve documentation coverage to 95%'
                    ],
                    'timeline': '2 weeks',
                    'budget_constraints': {
                        'max_cost_usd': 45.00,
                        'max_execution_time_hours': 4
                    }
                }
            },
            execution_context={
                'execution_preferences': {
                    'parallelization': 'aggressive',
                    'optimization_focus': 'balanced'
                },
                'quality_settings': {
                    'validation_level': 'strict'
                }
            },
            historical_context={
                'similar_goals': [
                    'code_quality_improvement_q1',
                    'documentation_enhancement_project'
                ]
            },
            priority='high',
            urgency='medium'
        )
        
        print(f"Input type: {workflow_input.input_type.value}")
        print(f"Goal objective: {workflow_input.content['goal']['objective']}")
        print(f"Success criteria count: {len(workflow_input.content['goal']['success_criteria'])}")
        
        # Execute workflow
        result = await orchestrator.execute_workflow(workflow_input)
        
        print(f"\nRESULT ANALYSIS:")
        print(f"  Success: {result.success}")
        print(f"  Agents spawned: {result.agents_spawned} (expected >= 4)")
        print(f"  Total cost: ${result.total_cost_usd} (budget: ${workflow_input.content['goal']['budget_constraints']['max_cost_usd']})")
        print(f"  Error message: {result.error_message}")
        
        print(f"\nCOMPLEXITY ANALYSIS:")
        complexity_data = result.metadata.get('complexity_analysis', {})
        if isinstance(complexity_data, dict):
            for key, value in complexity_data.items():
                print(f"  {key}: {value}")
        else:
            print(f"  complexity_analysis type: {type(complexity_data)}")
            print(f"  complexity_analysis value: {complexity_data}")
        
        print(f"\nSTRATEGY:")
        print(f"  Strategy used: {result.metadata.get('strategy_used')}")
        print(f"  Expected: recursive_decomposition or council_driven")
        
        await orchestrator.terminate()
        
    except Exception as e:
        print(f"❌ Debug error: {str(e)}")
        import traceback
        traceback.print_exc()

async def debug_monitoring_failure():
    """Debug monitoring and adaptation failure"""
    print("\n🔍 DEBUGGING MONITORING & ADAPTATION")
    print("-" * 50)
    
    try:
        orchestrator = TopLevelOrchestrator(
            max_concurrent_agents=3,  # Low limit to test adaptation
            max_execution_time_minutes=15,  # Tight time constraint
            max_cost_usd=20.0  # Low budget
        )
        
        await orchestrator.initialize()
        
        # Enable adaptation for testing
        orchestrator.strategy_adaptation_enabled = True
        
        # Create moderate complexity workflow
        workflow_input = WorkflowInput(
            input_type=WorkflowInputType.STRUCTURED_TASK,
            content={
                'task_definition': {
                    'primary_objective': 'Multi-step analysis and documentation',
                    'deliverables': ['analysis', 'summary', 'recommendations', 'implementation_plan']
                }
            },
            execution_context={
                'execution_preferences': {
                    'parallelization': 'aggressive'
                }
            }
        )
        
        print(f"Constraints: {orchestrator.max_concurrent_agents} agents, {orchestrator.max_execution_time_minutes}min, ${orchestrator.max_cost_usd}")
        
        # Execute workflow
        result = await orchestrator.execute_workflow(workflow_input)
        
        print(f"\nRESULT ANALYSIS:")
        print(f"  Success: {result.success}")
        print(f"  Agents spawned: {result.agents_spawned}")
        print(f"  Total cost: ${result.total_cost_usd}")
        
        print(f"\nMONITORING DATA:")
        monitoring_data = result.metadata.get('monitoring_final_state', {})
        print(f"  Monitoring data present: {len(monitoring_data) > 0}")
        if monitoring_data:
            for key, value in monitoring_data.items():
                print(f"    {key}: {value}")
        
        print(f"\nADAPTATION:")
        if hasattr(orchestrator, 'adaptation_triggers'):
            print(f"  Adaptation triggers: {orchestrator.adaptation_triggers}")
        else:
            print(f"  No adaptation_triggers attribute found")
        
        await orchestrator.terminate()
        
    except Exception as e:
        print(f"❌ Debug error: {str(e)}")
        import traceback
        traceback.print_exc()

async def debug_error_handling_failure():
    """Debug error handling failure"""
    print("\n🔍 DEBUGGING ERROR HANDLING")
    print("-" * 50)
    
    try:
        orchestrator = TopLevelOrchestrator(
            max_concurrent_agents=2,
            max_execution_time_minutes=5  # Very short time to potentially cause issues
        )
        
        await orchestrator.initialize()
        
        # Create workflow that might stress the system
        workflow_input = WorkflowInput(
            input_type=WorkflowInputType.STRUCTURED_TASK,
            content={
                'task_definition': {
                    'primary_objective': 'Handle potential failure scenarios gracefully',
                    'deliverables': ['analysis1', 'analysis2', 'synthesis']
                }
            },
            execution_context={
                'resource_limits': {
                    'max_concurrent_agents': 1  # Very restrictive
                }
            }
        )
        
        print(f"Stress test constraints: 2 agents max, 5min timeout, 1 concurrent agent limit")
        
        # Execute workflow
        result = await orchestrator.execute_workflow(workflow_input)
        
        print(f"\nRESULT ANALYSIS:")
        print(f"  Result exists: {result is not None}")
        if result:
            print(f"  Success: {result.success}")
            print(f"  Error message present: {result.error_message is not None}")
            print(f"  Error message: {result.error_message}")
            print(f"  Final output: {len(result.final_output) if result.final_output else 0} chars")
        
        print(f"\nORCHESTRATOR STATE:")
        status = await orchestrator.get_workflow_status()
        print(f"  Status keys: {list(status.keys())}")
        print(f"  Has orchestrator_id: {'orchestrator_id' in status}")
        
        print(f"\nAGENT CLEANUP:")
        if hasattr(orchestrator, 'current_active_agents'):
            print(f"  Active agents: {orchestrator.current_active_agents}")
        else:
            print(f"  No current_active_agents attribute")
        
        await orchestrator.terminate()
        
    except Exception as e:
        print(f"❌ Debug error: {str(e)}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all diagnostic tests"""
    await debug_structured_task_failure()
    await debug_goal_workflow_failure()
    await debug_monitoring_failure()
    await debug_error_handling_failure()

if __name__ == "__main__":
    asyncio.run(main())