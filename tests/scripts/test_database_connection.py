#!/usr/bin/env python3
"""
Test script to verify database connection and basic operations
Run this script to test the database setup independently
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.connection import db_manager
from database.models import Base, ThoughtTree, Agent, SystemConfig
from database.schemas import ThoughtTreeCreate, AgentCreate, SystemConfigCreate
from config.settings import settings
import uuid

async def test_database_connection():
    """Test basic database connectivity"""
    print("Testing database connection...")
    try:
        health = await db_manager.health_check()
        if health:
            print("✅ Database connection successful")
            return True
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

async def test_create_tables():
    """Test table creation"""
    print("\nCreating database tables...")
    try:
        await db_manager.create_tables()
        print("✅ Tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        return False

async def test_basic_crud_operations():
    """Test basic CRUD operations"""
    print("\nTesting basic CRUD operations...")
    
    try:
        async with db_manager.get_async_session() as session:
            # Test 1: Create a system config record
            config_data = SystemConfigCreate(
                config_key="test_max_recursion_depth",
                config_value={"value": 10},
                config_type="limit",
                description="Test configuration for max recursion depth"
            )
            
            config = SystemConfig(**config_data.model_dump())
            session.add(config)
            await session.commit()
            print("✅ System config created")
            
            # Test 2: Create a thought tree
            thought_data = ThoughtTreeCreate(
                goal="Test goal for database verification",
                parent_id=None,
                root_id=None
            )
            
            thought = ThoughtTree(**thought_data.model_dump())
            session.add(thought)
            await session.commit()
            await session.refresh(thought)
            print(f"✅ Thought tree created with ID: {thought.id}")
            
            # Test 3: Create an agent
            agent_data = AgentCreate(
                thought_tree_id=thought.id,
                agent_type="task",
                agent_class="TestAgent",
                spawned_by=None
            )
            
            agent = Agent(**agent_data.model_dump())
            session.add(agent)
            await session.commit()
            await session.refresh(agent)
            print(f"✅ Agent created with ID: {agent.id}")
            
            # Test 4: Query data back
            result_config = await session.get(SystemConfig, config.id)
            result_thought = await session.get(ThoughtTree, thought.id)
            result_agent = await session.get(Agent, agent.id)
            
            assert result_config.config_key == "test_max_recursion_depth"
            assert result_thought.goal == "Test goal for database verification"
            assert result_agent.agent_type == "task"
            
            print("✅ Data retrieval verified")
            
            return True
            
    except Exception as e:
        print(f"❌ CRUD operations failed: {e}")
        return False

async def test_relationships():
    """Test SQLAlchemy relationships"""
    print("\nTesting database relationships...")
    
    try:
        async with db_manager.get_async_session() as session:
            # Create parent thought tree
            parent_thought = ThoughtTree(
                goal="Parent goal",
                depth=0
            )
            session.add(parent_thought)
            await session.commit()
            await session.refresh(parent_thought)
            
            # Create child thought tree
            child_thought = ThoughtTree(
                goal="Child goal", 
                parent_id=parent_thought.id,
                root_id=parent_thought.id,
                depth=1
            )
            session.add(child_thought)
            await session.commit()
            await session.refresh(child_thought)
            
            # Test parent-child relationship
            assert child_thought.parent_id == parent_thought.id
            assert child_thought.root_id == parent_thought.id
            print("✅ Parent-child relationships working")
            
            return True
            
    except Exception as e:
        print(f"❌ Relationship test failed: {e}")
        return False

def print_database_info():
    """Print database configuration info"""
    print("Database Configuration:")
    print(f"  URL: {settings.database_url}")
    print(f"  Debug: {settings.debug}")
    print(f"  Default Max Recursion: {settings.default_max_recursion_depth}")
    print(f"  Default Max Agents: {settings.default_max_concurrent_agents}")
    print()

async def cleanup_test_data():
    """Clean up test data"""
    print("\nCleaning up test data...")
    try:
        async with db_manager.get_async_session() as session:
            # Note: In a real system we wouldn't delete data, but for testing it's okay
            from sqlalchemy import delete
            await session.execute(delete(Agent))
            await session.execute(delete(ThoughtTree))
            await session.execute(delete(SystemConfig).where(SystemConfig.config_key.like("test_%")))
            await session.commit()
            print("✅ Test data cleaned up")
    except Exception as e:
        print(f"⚠️  Cleanup failed (this is okay): {e}")

async def main():
    """Main test function"""
    print("=== NYX Database Connection Test ===")
    print_database_info()
    
    # Run tests
    tests = [
        ("Database Connection", test_database_connection()),
        ("Table Creation", test_create_tables()),
        ("CRUD Operations", test_basic_crud_operations()),
        ("Relationships", test_relationships())
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
    await cleanup_test_data()
    
    # Summary
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All database tests passed!")
        await db_manager.close()
        return 0
    else:
        print("💥 Some tests failed. Check your database configuration.")
        await db_manager.close()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())