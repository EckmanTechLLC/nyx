#!/usr/bin/env python3
"""
Test Council Agent Implementation  
Tests collaborative decision-making, multi-perspective analysis, and consensus building
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.agents.council import CouncilAgent, CouncilRole
from core.agents.base import AgentState
from llm.models import LLMModel

async def test_council_agent_initialization():
    """Test council agent initialization and composition"""
    print("🔍 TESTING COUNCIL AGENT INITIALIZATION")
    print("-" * 45)
    
    try:
        # Test default council composition
        agent = CouncilAgent()
        
        init_success = await agent.initialize()
        print(f"   Initialization: {'✅ SUCCESS' if init_success else '❌ FAILED'}")
        
        # Test council composition
        expected_roles = [CouncilRole.ENGINEER, CouncilRole.STRATEGIST, CouncilRole.DISSENTER]
        composition_correct = agent.council_composition == expected_roles
        print(f"   Default composition: {'✅ CORRECT' if composition_correct else '❌ INCORRECT'}")
        print(f"      Roles: {[role.value for role in agent.council_composition]}")
        
        # Test council members initialization
        members_initialized = len(agent.council_members) == len(expected_roles)
        print(f"   Members initialized: {'✅ SUCCESS' if members_initialized else '❌ FAILED'}")
        print(f"      Member count: {len(agent.council_members)}")
        
        # Test state
        state_correct = agent.state == AgentState.ACTIVE
        print(f"   Agent state: {'✅ ACTIVE' if state_correct else f'❌ {agent.state.value}'}")
        
        await agent.terminate()
        return init_success and composition_correct and members_initialized and state_correct
        
    except Exception as e:
        print(f"❌ Initialization test error: {str(e)}")
        return False

async def test_custom_council_composition():
    """Test custom council composition"""
    print(f"\n🎭 TESTING CUSTOM COUNCIL COMPOSITION")
    print("-" * 45)
    
    try:
        # Create council with custom composition
        custom_roles = [CouncilRole.ENGINEER, CouncilRole.ANALYST, CouncilRole.FACILITATOR]
        agent = CouncilAgent(council_composition=custom_roles)
        
        await agent.initialize()
        
        # Verify custom composition
        composition_correct = agent.council_composition == custom_roles
        print(f"   Custom composition: {'✅ CORRECT' if composition_correct else '❌ INCORRECT'}")
        
        # Verify all roles have perspective prompts
        all_roles_configured = all(
            role in agent.council_members for role in custom_roles
        )
        print(f"   All roles configured: {'✅ SUCCESS' if all_roles_configured else '❌ FAILED'}")
        
        # Test each role has appropriate configuration
        role_configs_valid = True
        for role in custom_roles:
            member = agent.council_members.get(role)
            if not member or not member.perspective_prompt:
                role_configs_valid = False
                break
        
        print(f"   Role configurations: {'✅ VALID' if role_configs_valid else '❌ INVALID'}")
        
        await agent.terminate()
        return composition_correct and all_roles_configured and role_configs_valid
        
    except Exception as e:
        print(f"❌ Custom composition test error: {str(e)}")
        return False

async def test_council_decision_process():
    """Test full council decision-making process"""
    print(f"\n🤝 TESTING COUNCIL DECISION PROCESS")
    print("-" * 45)
    
    try:
        agent = CouncilAgent()
        await agent.initialize()
        
        # Create a complex decision scenario
        decision_input = {
            'decision_context': '''
            Our software development team is considering whether to adopt a microservices architecture
            for our new e-commerce platform. The current monolithic system is becoming difficult to maintain
            and scale, but microservices introduce complexity in deployment, monitoring, and inter-service communication.
            
            Current system: 100k monthly active users, 5-person dev team
            Budget: $200k for redesign
            Timeline: 6 months to launch
            ''',
            'decision_question': 'Should we migrate to microservices architecture or optimize the existing monolith?',
            'additional_info': 'Team has limited microservices experience but strong monolith expertise',
            'constraints': 'Fixed budget, hard deadline, small team size',
            'success_criteria': 'Improved maintainability, better scalability, on-time delivery',
            'max_tokens_per_member': 800,
            'max_tokens_final': 1200
        }
        
        result = await agent.execute(decision_input)
        
        # Validate decision process
        process_success = result.success and len(result.content) > 500
        print(f"   Decision process: {'✅ COMPLETED' if process_success else '❌ FAILED'}")
        
        # Check for structured output
        decision_content = result.content.lower()
        expected_sections = ['recommendation', 'risk', 'implementation', 'monitoring']
        has_structured_output = all(section in decision_content for section in expected_sections)
        print(f"   Structured output: {'✅ COMPLETE' if has_structured_output else '❌ MISSING SECTIONS'}")
        
        # Check metadata
        metadata_complete = (
            result.metadata and 
            'council_composition' in result.metadata and
            'perspectives_gathered' in result.metadata and
            'session_phases_completed' in result.metadata
        )
        print(f"   Council metadata: {'✅ COMPLETE' if metadata_complete else '❌ INCOMPLETE'}")
        
        # Check token usage and cost
        resource_usage_valid = result.tokens_used > 0 and result.cost_usd > 0
        print(f"   Resource tracking: {'✅ VALID' if resource_usage_valid else '❌ INVALID'}")
        print(f"      Total tokens: {result.tokens_used:,}")
        print(f"      Total cost: ${result.cost_usd:.6f}")
        
        # Display sample of decision
        print(f"   Decision sample: {result.content[:200]}...")
        
        await agent.terminate()
        return process_success and has_structured_output and metadata_complete and resource_usage_valid
        
    except Exception as e:
        print(f"❌ Decision process test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_council_input_validation():
    """Test council agent input validation"""
    print(f"\n🛡️ TESTING COUNCIL INPUT VALIDATION")
    print("-" * 45)
    
    try:
        agent = CouncilAgent()
        await agent.initialize()
        
        # Test various invalid inputs
        invalid_inputs = [
            {},  # Empty input
            {'decision_context': 'Some context'},  # Missing decision_question
            {'decision_question': 'What should we do?'},  # Missing decision_context
            {'decision_context': 'Too short', 'decision_question': 'Also too short'},  # Content too short
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

async def test_council_statistics():
    """Test council statistics tracking"""
    print(f"\n📊 TESTING COUNCIL STATISTICS")
    print("-" * 45)
    
    try:
        agent = CouncilAgent()
        await agent.initialize()
        
        # Execute a decision to generate statistics
        simple_decision = {
            'decision_context': 'We need to choose between two project management tools for our team of 10 developers.',
            'decision_question': 'Should we use Tool A or Tool B?',
            'max_tokens_per_member': 300
        }
        
        await agent.execute(simple_decision)
        
        # Get statistics
        stats = await agent.get_council_statistics()
        
        # Validate statistics structure
        required_stats = [
            'council_composition', 'total_sessions', 'session_success_rate',
            'agent_id', 'agent_type', 'total_executions'
        ]
        
        stats_complete = all(key in stats for key in required_stats)
        print(f"   Statistics structure: {'✅ COMPLETE' if stats_complete else '❌ INCOMPLETE'}")
        
        # Validate statistics values
        values_valid = (
            stats['total_sessions'] == 1 and
            stats['agent_type'] == 'council' and
            len(stats['council_composition']) == 3 and
            stats['session_success_rate'] > 0
        )
        print(f"   Statistics values: {'✅ VALID' if values_valid else '❌ INVALID'}")
        
        print(f"      Sessions: {stats['total_sessions']}")
        print(f"      Success rate: {stats['session_success_rate']:.2f}")
        print(f"      Council size: {len(stats['council_composition'])}")
        
        await agent.terminate()
        return stats_complete and values_valid
        
    except Exception as e:
        print(f"❌ Statistics test error: {str(e)}")
        return False

async def main():
    """Run all council agent tests"""
    print("🚀 COUNCIL AGENT TESTING")
    print("=" * 60)
    
    try:
        # Run all tests
        init_passed = await test_council_agent_initialization()
        composition_passed = await test_custom_council_composition()
        decision_passed = await test_council_decision_process()
        validation_passed = await test_council_input_validation()
        stats_passed = await test_council_statistics()
        
        print(f"\n" + "=" * 60)
        print("📊 TEST RESULTS:")
        print(f"   Initialization: {'✅ PASSED' if init_passed else '❌ FAILED'}")
        print(f"   Custom composition: {'✅ PASSED' if composition_passed else '❌ FAILED'}")
        print(f"   Decision process: {'✅ PASSED' if decision_passed else '❌ FAILED'}")
        print(f"   Input validation: {'✅ PASSED' if validation_passed else '❌ FAILED'}")
        print(f"   Statistics tracking: {'✅ PASSED' if stats_passed else '❌ FAILED'}")
        
        overall_success = all([init_passed, composition_passed, decision_passed, validation_passed, stats_passed])
        
        if overall_success:
            print(f"\n🎉 ALL COUNCIL AGENT TESTS PASSED!")
            print("   ✅ Council composition and initialization working")
            print("   ✅ Multi-perspective decision-making operational")
            print("   ✅ Structured decision output with comprehensive analysis")
            print("   ✅ Input validation preventing invalid council sessions")
            print("   ✅ Statistics tracking council performance metrics")
        else:
            print(f"\n❌ SOME COUNCIL AGENT TESTS FAILED")
            print("   Review individual test results for specific issues")
        
        return overall_success
        
    except Exception as e:
        print(f"💥 Council agent testing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)