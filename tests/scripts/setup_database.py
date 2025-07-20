#!/usr/bin/env python3
"""
Script to create the NYX database and run initial setup
Run this before the database connection test
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from config.settings import settings
from database.connection import db_manager
from database.models import SystemConfig
import uuid

def create_user_and_database():
    """Create NYX user and database"""
    print("Setting up NYX user and database...")
    
    # Parse connection string to get components
    url_parts = settings.database_url.replace('postgresql://', '').split('/')
    db_name = url_parts[-1]  # 'nyx'
    user_part = url_parts[0].split('@')[0]  # 'user:pass'
    host_part = url_parts[0].split('@')[1]  # 'host:port'
    nyx_user = user_part.split(':')[0]
    nyx_password = user_part.split(':')[1]
    
    # Connect to postgres database as postgres superuser
    postgres_url = f"postgresql://postgres:Aim33IsReal!@{host_part}/postgres"
    
    try:
        # Connect to postgres database
        conn = psycopg2.connect(postgres_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (nyx_user,))
        user_exists = cursor.fetchone()
        
        if not user_exists:
            cursor.execute(f"CREATE USER {nyx_user} WITH PASSWORD %s", (nyx_password,))
            print(f"✅ User '{nyx_user}' created successfully")
        else:
            print(f"✅ User '{nyx_user}' already exists")
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (db_name,))
        db_exists = cursor.fetchone()
        
        if not db_exists:
            cursor.execute(f'CREATE DATABASE "{db_name}" OWNER {nyx_user}')
            print(f"✅ Database '{db_name}' created successfully")
        else:
            print(f"✅ Database '{db_name}' already exists")
        
        # Grant permissions to the user
        cursor.execute(f'GRANT ALL PRIVILEGES ON DATABASE "{db_name}" TO {nyx_user}')
        print(f"✅ Granted permissions to '{nyx_user}' on database '{db_name}'")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed to create user/database: {e}")
        return False

async def setup_initial_config():
    """Set up initial system configuration"""
    print("Setting up initial system configuration...")
    
    try:
        async with db_manager.get_async_session() as session:
            # Initial system configurations
            configs = [
                {
                    "config_key": "max_recursion_depth",
                    "config_value": {"value": 10},
                    "config_type": "limit",
                    "description": "Maximum depth for recursive agent spawning"
                },
                {
                    "config_key": "max_concurrent_agents",
                    "config_value": {"value": 50},
                    "config_type": "limit", 
                    "description": "Maximum number of concurrent agents system-wide"
                },
                {
                    "config_key": "max_thought_tree_age_days",
                    "config_value": {"value": 365},
                    "config_type": "limit",
                    "description": "Maximum age before thought trees marked as archival"
                },
                {
                    "config_key": "default_retry_attempts",
                    "config_value": {"value": 3},
                    "config_type": "setting",
                    "description": "Default number of retry attempts for failed operations"
                },
                {
                    "config_key": "llm_timeout_seconds", 
                    "config_value": {"value": 60},
                    "config_type": "setting",
                    "description": "Default timeout for LLM API calls"
                },
                {
                    "config_key": "tool_timeout_seconds",
                    "config_value": {"value": 30},
                    "config_type": "setting", 
                    "description": "Default timeout for tool executions"
                }
            ]
            
            from sqlalchemy import text
            for config_data in configs:
                # Check if config already exists
                existing = await session.execute(
                    text("SELECT id FROM system_config WHERE config_key = :key"),
                    {"key": config_data["config_key"]}
                )
                if not existing.fetchone():
                    config = SystemConfig(
                        id=uuid.uuid4(),
                        **config_data
                    )
                    session.add(config)
            
            await session.commit()
            print(f"✅ Initial configuration set up ({len(configs)} settings)")
            return True
            
    except Exception as e:
        print(f"❌ Failed to set up initial config: {e}")
        return False

async def main():
    """Main setup function"""
    print("=== NYX Database Setup ===")
    print(f"Target Database: {settings.database_url}")
    print()
    
    # Step 1: Create user and database
    if not create_user_and_database():
        print("💥 User/Database creation failed. Cannot proceed.")
        return 1
    
    # Step 2: Create tables
    print("\nCreating database tables...")
    try:
        await db_manager.create_tables()
        print("✅ Tables created successfully")
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        return 1
    
    # Step 3: Set up initial configuration
    if not await setup_initial_config():
        print("💥 Initial configuration setup failed.")
        return 1
    
    print("\n🎉 Database setup completed successfully!")
    print("You can now run the database connection test:")
    print("python tests/scripts/test_database_connection.py")
    
    await db_manager.close()
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)