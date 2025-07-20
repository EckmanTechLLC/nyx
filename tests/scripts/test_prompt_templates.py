#!/usr/bin/env python3
"""
Test script for prompt template management system
Tests template CRUD operations, rendering, and database integration
"""
import asyncio
import sys
import os
from pathlib import Path
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from llm.prompt_templates import PromptTemplateManager, PromptTemplateError
from database.connection import db_manager

async def test_template_creation():
    """Test creating prompt templates"""
    print("Testing template creation...")
    
    try:
        manager = PromptTemplateManager()
        
        # Create a simple template
        template = await manager.create_template(
            name="test_greeting",
            content="Hello {name}, welcome to {system}! How can I help you today?",
            template_type="user",
            created_by="test_script"
        )
        
        if template and template.name == "test_greeting":
            print("✅ Template creation successful")
            print(f"   Template ID: {template.id}")
            print(f"   Variables: {template.variables}")
            print(f"   Version: {template.version}")
            return True
        else:
            print("❌ Template creation failed")
            return False
            
    except Exception as e:
        print(f"❌ Template creation error: {e}")
        return False

async def test_template_variable_extraction():
    """Test automatic variable extraction"""
    print("\nTesting variable extraction...")
    
    try:
        manager = PromptTemplateManager()
        
        # Create template with multiple variables
        template = await manager.create_template(
            name="test_complex",
            content="""
You are a {role} in a {company_type} company.
Your task is to analyze {topic} and provide {output_format} recommendations.
The target audience is {audience} and the deadline is {deadline}.
Please consider {constraints} in your analysis.
""",
            template_type="system",
            created_by="test_script"
        )
        
        expected_vars = ['role', 'company_type', 'topic', 'output_format', 'audience', 'deadline', 'constraints']
        
        if template and set(template.variables) == set(expected_vars):
            print("✅ Variable extraction working correctly")
            print(f"   Extracted variables: {sorted(template.variables)}")
            return True
        else:
            print("❌ Variable extraction failed")
            print(f"   Expected: {sorted(expected_vars)}")
            print(f"   Got: {sorted(template.variables) if template else 'None'}")
            return False
            
    except Exception as e:
        print(f"❌ Variable extraction error: {e}")
        return False

async def test_template_rendering():
    """Test template rendering with variables"""
    print("\nTesting template rendering...")
    
    try:
        manager = PromptTemplateManager()
        
        # Render the greeting template
        rendered = await manager.render_template(
            name="test_greeting",
            variables={
                "name": "Alice",
                "system": "NYX"
            }
        )
        
        expected = "Hello Alice, welcome to NYX! How can I help you today?"
        
        if rendered == expected:
            print("✅ Template rendering successful")
            print(f"   Rendered: {rendered}")
            return True
        else:
            print("❌ Template rendering failed")
            print(f"   Expected: {expected}")
            print(f"   Got: {rendered}")
            return False
            
    except Exception as e:
        print(f"❌ Template rendering error: {e}")
        return False

async def test_template_variable_validation():
    """Test template variable validation"""
    print("\nTesting variable validation...")
    
    try:
        manager = PromptTemplateManager()
        
        # Test with missing variables
        missing = await manager.validate_template_variables(
            name="test_complex",
            variables={
                "role": "analyst",
                "company_type": "tech",
                "topic": "market trends"
                # Missing: output_format, audience, deadline, constraints
            }
        )
        
        expected_missing = ['audience', 'constraints', 'deadline', 'output_format']
        
        if set(missing) == set(expected_missing):
            print("✅ Variable validation working correctly")
            print(f"   Missing variables detected: {sorted(missing)}")
            return True
        else:
            print("❌ Variable validation failed")
            print(f"   Expected missing: {sorted(expected_missing)}")
            print(f"   Got missing: {sorted(missing)}")
            return False
            
    except Exception as e:
        print(f"❌ Variable validation error: {e}")
        return False

async def test_template_versioning():
    """Test template versioning when content changes"""
    print("\nTesting template versioning...")
    
    try:
        manager = PromptTemplateManager()
        
        # Get current version
        original = await manager.get_template("test_greeting")
        if not original:
            print("❌ Could not find original template")
            return False
        
        original_version = original.version
        
        # Update template content (should create new version)
        updated = await manager.update_template(
            name="test_greeting",
            content="Hi {name}! Welcome to {system}. What would you like to do?"
        )
        
        if updated and updated.version == original_version + 1:
            print("✅ Template versioning working correctly")
            print(f"   Original version: {original_version}")
            print(f"   New version: {updated.version}")
            print(f"   New content: {updated.content[:50]}...")
            return True
        else:
            print("❌ Template versioning failed")
            print(f"   Original version: {original_version}")
            print(f"   Updated version: {updated.version if updated else 'None'}")
            return False
            
    except Exception as e:
        print(f"❌ Template versioning error: {e}")
        return False

async def test_template_listing():
    """Test listing templates with filters"""
    print("\nTesting template listing...")
    
    try:
        manager = PromptTemplateManager()
        
        # List all active templates
        all_templates = await manager.list_templates(active_only=True)
        
        if len(all_templates) >= 2:  # Should have at least our test templates
            print("✅ Template listing working")
            print(f"   Found {len(all_templates)} active templates:")
            for template in all_templates[:3]:  # Show first 3
                print(f"     - {template.name} (v{template.version}, {template.template_type})")
            
            # Test filtering by type
            user_templates = await manager.list_templates(template_type="user", active_only=True)
            system_templates = await manager.list_templates(template_type="system", active_only=True)
            
            print(f"   User templates: {len(user_templates)}")
            print(f"   System templates: {len(system_templates)}")
            
            return True
        else:
            print("❌ Template listing failed - insufficient templates found")
            print(f"   Found: {len(all_templates)} templates")
            return False
            
    except Exception as e:
        print(f"❌ Template listing error: {e}")
        return False

async def test_template_usage_stats():
    """Test template usage statistics tracking"""
    print("\nTesting usage statistics...")
    
    try:
        manager = PromptTemplateManager()
        
        # Get initial stats
        initial_stats = await manager.get_template_stats("test_greeting")
        if not initial_stats:
            print("❌ Could not get initial stats")
            return False
        
        initial_usage = initial_stats["usage_count"]
        
        # Use the template a few times
        for i in range(3):
            try:
                await manager.render_template(
                    name="test_greeting",
                    variables={"name": f"User{i}", "system": "NYX"}
                )
            except:
                pass  # Errors will be tracked in stats
        
        # Wait for async stats updates
        await asyncio.sleep(1)
        
        # Check updated stats
        updated_stats = await manager.get_template_stats("test_greeting")
        
        if updated_stats and updated_stats["usage_count"] > initial_usage:
            print("✅ Usage statistics tracking working")
            print(f"   Initial usage: {initial_usage}")
            print(f"   Updated usage: {updated_stats['usage_count']}")
            print(f"   Success rate: {updated_stats['success_rate']:.2%}")
            return True
        else:
            print("❌ Usage statistics not updating")
            print(f"   Initial: {initial_usage}")
            print(f"   Updated: {updated_stats['usage_count'] if updated_stats else 'None'}")
            return False
            
    except Exception as e:
        print(f"❌ Usage statistics error: {e}")
        return False

async def test_template_error_handling():
    """Test error handling for invalid operations"""
    print("\nTesting error handling...")
    
    try:
        manager = PromptTemplateManager()
        
        # Test rendering with missing variables
        try:
            await manager.render_template(
                name="test_complex",
                variables={"role": "analyst"}  # Missing many required variables
            )
            print("❌ Should have failed with missing variables")
            return False
        except PromptTemplateError as e:
            print("✅ Missing variable error handled correctly")
            print(f"   Error: {str(e)[:60]}...")
        
        # Test getting non-existent template
        template = await manager.get_template("non_existent_template")
        if template is None:
            print("✅ Non-existent template handled correctly")
        else:
            print("❌ Should return None for non-existent template")
            return False
        
        # Test creating duplicate template name
        try:
            await manager.create_template(
                name="test_greeting",  # Already exists
                content="Duplicate template",
                created_by="test_script"
            )
            print("❌ Should have failed with duplicate name")
            return False
        except PromptTemplateError as e:
            print("✅ Duplicate template name error handled correctly")
            print(f"   Error: {str(e)[:60]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

async def cleanup_test_templates():
    """Clean up test templates"""
    print("\nCleaning up test templates...")
    
    try:
        manager = PromptTemplateManager()
        
        test_templates = ["test_greeting", "test_complex"]
        cleaned = 0
        
        for template_name in test_templates:
            success = await manager.delete_template(template_name)
            if success:
                cleaned += 1
        
        print(f"✅ Cleaned up {cleaned} test templates")
        return True
        
    except Exception as e:
        print(f"⚠️  Cleanup failed (this is okay): {e}")
        return True  # Don't fail the test suite for cleanup issues

async def main():
    """Main test function"""
    print("=== Prompt Template Management Test Suite ===")
    print(f"Database: {db_manager.async_engine.url}")
    print()
    
    # Run tests in order
    tests = [
        ("Template Creation", test_template_creation()),
        ("Variable Extraction", test_template_variable_extraction()),
        ("Template Rendering", test_template_rendering()),
        ("Variable Validation", test_template_variable_validation()),
        ("Template Versioning", test_template_versioning()),
        ("Template Listing", test_template_listing()),
        ("Usage Statistics", test_template_usage_stats()),
        ("Error Handling", test_template_error_handling())
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_coro in tests:
        try:
            result = await test_coro
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    # Cleanup
    await cleanup_test_templates()
    
    # Summary
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All prompt template tests passed!")
        await db_manager.close()
        return 0
    else:
        print("💥 Some tests failed. Check your database configuration.")
        await db_manager.close()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)