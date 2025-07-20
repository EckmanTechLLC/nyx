#!/usr/bin/env python3
"""
Test Task Agent Implementation
Tests task execution, different task types, and bounded function execution
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.agents.task import TaskAgent, TaskSpec
from core.agents.base import AgentState
from llm.models import LLMModel

async def test_task_agent_initialization():
    """Test task agent initialization and configuration"""
    print("🔍 TESTING TASK AGENT INITIALIZATION")
    print("-" * 40)
    
    try:
        agent = TaskAgent()
        
        # Test initialization
        init_success = await agent.initialize()
        print(f"   Initialization: {'✅ SUCCESS' if init_success else '❌ FAILED'}")
        
        # Test supported task types
        supported_types = agent.get_supported_task_types()
        expected_types = {
            'document_generation', 'code_synthesis', 'data_analysis',
            'content_summary', 'content_transformation', 'structured_extraction',
            'creative_writing', 'technical_writing'
        }
        
        types_correct = expected_types.issubset(supported_types)
        print(f"   Task types: {'✅ ALL SUPPORTED' if types_correct else '❌ MISSING TYPES'}")
        print(f"      Supported: {len(supported_types)} types")
        
        # Test state
        state_correct = agent.state == AgentState.ACTIVE
        print(f"   Agent state: {'✅ ACTIVE' if state_correct else f'❌ {agent.state.value}'}")
        
        await agent.terminate()
        return init_success and types_correct and state_correct
        
    except Exception as e:
        print(f"❌ Initialization test error: {str(e)}")
        return False

async def test_document_generation_task():
    """Test document generation task"""
    print(f"\n📄 TESTING DOCUMENT GENERATION")
    print("-" * 40)
    
    try:
        agent = TaskAgent()
        await agent.initialize()
        
        task_input = {
            'task_type': 'document_generation',
            'description': 'Create a brief project status report',
            'content': 'Project: NYX Agent System\nStatus: Core agents implemented\nNext: Testing and integration',
            'output_format': 'Professional report format',
            'max_tokens': 500
        }
        
        result = await agent.execute(task_input)
        
        # Validate result
        task_success = (result.success and 
                       len(result.content) > 100 and
                       result.tokens_used > 0 and
                       result.cost_usd > 0)
        
        print(f"   Execution: {'✅ SUCCESS' if task_success else '❌ FAILED'}")
        print(f"   Content length: {len(result.content)} chars")
        print(f"   Tokens used: {result.tokens_used}")
        print(f"   Cost: ${result.cost_usd:.6f}")
        print(f"   Sample: {result.content[:100]}...")
        
        await agent.terminate()
        return task_success
        
    except Exception as e:
        print(f"❌ Document generation error: {str(e)}")
        return False

async def test_code_synthesis_task():
    """Test code synthesis task"""
    print(f"\n💻 TESTING CODE SYNTHESIS")
    print("-" * 40)
    
    try:
        agent = TaskAgent()
        await agent.initialize()
        
        task_input = {
            'task_type': 'code_synthesis',
            'description': 'Create a simple Python function',
            'content': 'Create a function that calculates the factorial of a number',
            'language': 'Python',
            'max_tokens': 300,
            'temperature': 0.3  # Lower temperature for code
        }
        
        result = await agent.execute(task_input)
        
        # Validate result
        code_indicators = ['def ', 'factorial', 'return']
        has_code_structure = all(indicator in result.content for indicator in code_indicators)
        
        task_success = (result.success and 
                       has_code_structure and
                       result.tokens_used > 0)
        
        print(f"   Execution: {'✅ SUCCESS' if task_success else '❌ FAILED'}")
        print(f"   Code structure: {'✅ VALID' if has_code_structure else '❌ INVALID'}")
        print(f"   Tokens used: {result.tokens_used}")
        print(f"   Code preview: {result.content[:150]}...")
        
        await agent.terminate()
        return task_success
        
    except Exception as e:
        print(f"❌ Code synthesis error: {str(e)}")
        return False

async def test_task_spec_interface():
    """Test TaskSpec convenience interface"""
    print(f"\n📋 TESTING TASK SPEC INTERFACE")
    print("-" * 40)
    
    try:
        agent = TaskAgent()
        await agent.initialize()
        
        # Create TaskSpec
        task_spec = TaskSpec(
            task_type='content_summary',
            description='Summarize the key points from the given text',
            input_data='The NYX agent system consists of multiple specialized agents: TaskAgent for bounded functions, CouncilAgent for collaborative decisions, ValidatorAgent for rule enforcement, and MemoryAgent for context management. Each agent integrates with the LLM system and provides comprehensive logging.',
            expected_output_format='Bulleted list of key points',
            max_tokens=200
        )
        
        result = await agent.execute_task(task_spec)
        
        # Validate result
        summary_indicators = ['agent', 'task', 'council', 'validator', 'memory']
        has_summary_content = any(indicator in result.content.lower() for indicator in summary_indicators)
        
        task_success = (result.success and 
                       has_summary_content and
                       len(result.content) > 50)
        
        print(f"   TaskSpec execution: {'✅ SUCCESS' if task_success else '❌ FAILED'}")
        print(f"   Summary content: {'✅ RELEVANT' if has_summary_content else '❌ IRRELEVANT'}")
        print(f"   Content length: {len(result.content)} chars")
        print(f"   Summary: {result.content[:120]}...")
        
        await agent.terminate()
        return task_success
        
    except Exception as e:
        print(f"❌ TaskSpec test error: {str(e)}")
        return False

async def test_input_validation():
    """Test input validation and error handling"""
    print(f"\n🛡️ TESTING INPUT VALIDATION")
    print("-" * 40)
    
    try:
        agent = TaskAgent()
        await agent.initialize()
        
        # Test missing required fields
        invalid_inputs = [
            {},  # Empty input
            {'task_type': 'document_generation'},  # Missing description
            {'description': 'Test task'},  # Missing task_type
            {'task_type': 'invalid_type', 'description': 'Test', 'content': 'Test'},  # Invalid task type
        ]
        
        validation_results = []
        for i, invalid_input in enumerate(invalid_inputs):
            result = await agent.execute(invalid_input)
            validation_failed_correctly = not result.success and result.error_message
            validation_results.append(validation_failed_correctly)
            print(f"   Invalid input {i+1}: {'✅ REJECTED' if validation_failed_correctly else '❌ ACCEPTED'}")
        
        all_validation_correct = all(validation_results)
        
        await agent.terminate()
        return all_validation_correct
        
    except Exception as e:
        print(f"❌ Input validation test error: {str(e)}")
        return False

async def main():
    """Run all task agent tests"""
    print("🚀 TASK AGENT TESTING")
    print("=" * 60)
    
    try:
        # Run all tests
        init_passed = await test_task_agent_initialization()
        doc_gen_passed = await test_document_generation_task()
        code_passed = await test_code_synthesis_task() 
        spec_passed = await test_task_spec_interface()
        validation_passed = await test_input_validation()
        
        print(f"\n" + "=" * 60)
        print("📊 TEST RESULTS:")
        print(f"   Initialization: {'✅ PASSED' if init_passed else '❌ FAILED'}")
        print(f"   Document generation: {'✅ PASSED' if doc_gen_passed else '❌ FAILED'}")
        print(f"   Code synthesis: {'✅ PASSED' if code_passed else '❌ FAILED'}")
        print(f"   TaskSpec interface: {'✅ PASSED' if spec_passed else '❌ FAILED'}")
        print(f"   Input validation: {'✅ PASSED' if validation_passed else '❌ FAILED'}")
        
        overall_success = all([init_passed, doc_gen_passed, code_passed, spec_passed, validation_passed])
        
        if overall_success:
            print(f"\n🎉 ALL TASK AGENT TESTS PASSED!")
            print("   ✅ Task agent initialization and configuration working")
            print("   ✅ Document generation producing quality output")
            print("   ✅ Code synthesis creating valid code structures")
            print("   ✅ TaskSpec interface providing convenient task execution")
            print("   ✅ Input validation preventing invalid executions")
        else:
            print(f"\n❌ SOME TASK AGENT TESTS FAILED")
            print("   Review individual test results for specific issues")
        
        return overall_success
        
    except Exception as e:
        print(f"💥 Task agent testing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)