#!/usr/bin/env python3
"""
Debug TopLevelOrchestrator strategy selection
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

async def debug_strategy_selection():
    """Debug strategy selection for simple input"""
    print("🔍 DEBUG STRATEGY SELECTION")
    print("-" * 40)
    
    try:
        orchestrator = TopLevelOrchestrator()
        await orchestrator.initialize()
        
        # Test simple user prompt
        simple_input = WorkflowInput(
            input_type=WorkflowInputType.USER_PROMPT,
            content={'content': 'What is Python?'},
            priority='low',
            urgency='normal'
        )
        
        print(f"Input: {simple_input.content}")
        print(f"Priority: {simple_input.priority}, Urgency: {simple_input.urgency}")
        
        # Analyze complexity
        complexity = await orchestrator._analyze_complexity(simple_input)
        print(f"Complexity Analysis:")
        print(f"  - Cognitive: {complexity.cognitive_complexity.value}")
        print(f"  - Technical: {complexity.technical_complexity.value}")
        print(f"  - Coordination: {complexity.coordination_complexity.value}")
        print(f"  - Overall: {complexity.overall_complexity().value}")
        print(f"  - Requires decomposition: {complexity.requires_decomposition()}")
        
        # Select strategy
        strategy = await orchestrator._select_strategy(simple_input, complexity)
        print(f"Selected Strategy: {strategy.value}")
        print(f"Expected: {WorkflowStrategy.DIRECT_EXECUTION.value}")
        print(f"Match: {strategy == WorkflowStrategy.DIRECT_EXECUTION}")
        
        await orchestrator.terminate()
        
        return strategy == WorkflowStrategy.DIRECT_EXECUTION
        
    except Exception as e:
        print(f"❌ Debug error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_strategy_selection())
    sys.exit(0 if success else 1)