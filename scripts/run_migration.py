#!/usr/bin/env python3
"""
Script to run database migration for motivational model tables
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.models import Base, MotivationalState, MotivationalTask
from database.connection import db_manager
from sqlalchemy import MetaData

async def run_migration():
    """Create motivational model tables directly"""
    try:
        print("🔄 Creating motivational model tables...")
        
        engine = db_manager.async_engine
        async with engine.begin() as conn:
            # Get the metadata to check existing tables
            meta = MetaData()
            await conn.run_sync(meta.reflect)
            
            # Create motivational tables that don't exist
            motivational_tables = [MotivationalState.__table__, MotivationalTask.__table__]
            
            for table in motivational_tables:
                if table.name not in meta.tables:
                    print(f"Creating table: {table.name}")
                    await conn.run_sync(table.create)
                else:
                    print(f"Table already exists: {table.name}")
        
        print("✅ Tables created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main execution"""
    print("🚀 NYX Motivational Model Database Setup")
    print("=" * 50)
    
    success = await run_migration()
    
    if success:
        print("\n🎉 Database setup completed successfully!")
        print("You can now run the motivational model tests.")
        return 0
    else:
        print("\n❌ Database setup failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)