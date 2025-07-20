#!/usr/bin/env python3
"""
Debug goal-based workflow failures
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
    WorkflowInputType
)

async def debug_goal_workflow():
    """Debug goal workflow specific issues"""
    print("🔍 DEBUGGING GOAL-BASED WORKFLOW DETAILS")
    print("-" * 60)
    
    try:
        orchestrator = TopLevelOrchestrator(
            max_concurrent_agents=10,
            max_execution_time_minutes=60,
            max_cost_usd=50.0
        )
        
        await orchestrator.initialize()
        
        # Create goal-based workflow input (same as test)
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
        print(f"Priority: {workflow_input.priority}, Urgency: {workflow_input.urgency}")
        
        # Execute workflow
        result = await orchestrator.execute_workflow(workflow_input)
        
        print(f"\n📊 DETAILED RESULT ANALYSIS:")
        print(f"  Overall success: {result.success}")
        print(f"  Agents spawned: {result.agents_spawned}")
        print(f"  Total cost: ${result.total_cost_usd}")
        print(f"  Budget limit: ${workflow_input.content['goal']['budget_constraints']['max_cost_usd']}")
        
        print(f"\n🔍 COMPLEXITY ANALYSIS DEBUG:")
        complexity_data = result.metadata.get('complexity_analysis', {})
        print(f"  Raw complexity_analysis: {complexity_data}")
        
        if hasattr(complexity_data, 'cognitive_complexity'):
            print(f"  cognitive_complexity object: {complexity_data.cognitive_complexity}")
            print(f"  cognitive_complexity value: {complexity_data.cognitive_complexity.value}")
        elif isinstance(complexity_data, dict):
            cog_complex = complexity_data.get('cognitive_complexity')
            print(f"  cognitive_complexity from dict: {cog_complex}")
            if hasattr(cog_complex, 'value'):
                print(f"  cognitive_complexity.value: {cog_complex.value}")
        
        print(f"\n🎯 STRATEGY ANALYSIS:")
        strategy_used = result.metadata.get('strategy_used')
        print(f"  Strategy used: {strategy_used}")
        print(f"  Strategy type: {type(strategy_used)}")
        if hasattr(strategy_used, 'value'):
            print(f"  Strategy value: {strategy_used.value}")
        
        print(f"\n📋 TEST CONDITION CHECKS:")
        # Check 1: High complexity handling
        complexity_is_high = False
        if isinstance(complexity_data, dict):
            cog_complex = complexity_data.get('cognitive_complexity')
            if hasattr(cog_complex, 'value'):
                complexity_is_high = cog_complex.value == 'high'
            else:
                complexity_is_high = str(cog_complex) == 'high'
        
        strategy_is_complex = False
        if hasattr(strategy_used, 'value'):
            strategy_is_complex = strategy_used.value in ['recursive_decomposition', 'council_driven']
        else:
            strategy_is_complex = str(strategy_used) in ['recursive_decomposition', 'council_driven']
        
        high_complexity_handled = complexity_is_high or strategy_is_complex
        print(f"  High complexity handled: {high_complexity_handled} (complexity: {complexity_is_high}, strategy: {strategy_is_complex})")
        
        # Check 2: Goal decomposition
        goal_decomposition = result.agents_spawned >= 4
        print(f"  Goal decomposition (≥4 agents): {goal_decomposition} ({result.agents_spawned} agents)")
        
        # Check 3: Budget adherence
        budget_ok = result.total_cost_usd <= workflow_input.content['goal']['budget_constraints']['max_cost_usd']
        print(f"  Budget adherence: {budget_ok}")
        
        print(f"\n🏁 FINAL TEST RESULTS:")
        print(f"  High complexity handling: {'✅ PASS' if high_complexity_handled else '❌ FAIL'}")
        print(f"  Goal decomposition: {'✅ PASS' if goal_decomposition else '❌ FAIL'}")
        print(f"  Budget adherence: {'✅ PASS' if budget_ok else '❌ FAIL'}")
        
        overall_pass = result.success and high_complexity_handled and goal_decomposition and budget_ok
        print(f"  Overall goal workflow test: {'✅ PASS' if overall_pass else '❌ FAIL'}")
        
        await orchestrator.terminate()
        
    except Exception as e:
        print(f"❌ Debug error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_goal_workflow())