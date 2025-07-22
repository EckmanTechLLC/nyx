#!/usr/bin/env python3
"""
Basic test to verify FastAPI application can start up correctly.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def test_imports():
    """Test that all necessary imports work"""
    print("Testing imports...")
    
    try:
        from app.main import app
        print("✅ FastAPI app imports successfully")
    except Exception as e:
        print(f"❌ FastAPI app import failed: {e}")
        return False
    
    try:
        from app.core.config import get_settings, get_fastapi_settings
        print("✅ Configuration imports successfully")
    except Exception as e:
        print(f"❌ Configuration import failed: {e}")
        return False
    
    try:
        from app.core.database import get_db_session, check_database_health
        print("✅ Database utilities import successfully")
    except Exception as e:
        print(f"❌ Database utilities import failed: {e}")
        return False
    
    try:
        from app.api.v1.system import router
        print("✅ System API router imports successfully")
    except Exception as e:
        print(f"❌ System API router import failed: {e}")
        return False
        
    try:
        from app.api.v1.orchestrator import router
        print("✅ Orchestrator API router imports successfully")
    except Exception as e:
        print(f"❌ Orchestrator API router import failed: {e}")
        return False
        
    try:
        from app.api.v1.motivational import router
        print("✅ Motivational API router imports successfully")
    except Exception as e:
        print(f"❌ Motivational API router import failed: {e}")
        return False
    
    return True

def test_app_creation():
    """Test that FastAPI app can be created"""
    try:
        from app.main import app
        
        # Check basic app properties
        assert app.title == "NYX Autonomous Agent API"
        assert app.version == "1.0.0"
        
        # Check that routes are registered
        routes = [route.path for route in app.routes]
        expected_routes = [
            "/health", "/", 
            "/api/v1/system/health", "/api/v1/system/status", "/api/v1/system/info",
            "/api/v1/orchestrator/workflows/execute",
            "/api/v1/orchestrator/workflows/{workflow_id}/status",
            "/api/v1/orchestrator/workflows/active",
            "/api/v1/orchestrator/strategies",
            "/api/v1/orchestrator/input-types",
            "/api/v1/motivational/engine/start",
            "/api/v1/motivational/engine/stop",
            "/api/v1/motivational/engine/status",
            "/api/v1/motivational/states",
            "/api/v1/motivational/states/{motivation_type}/boost",
            "/api/v1/motivational/states/{motivation_type}",
            "/api/v1/motivational/tasks/recent",
            "/api/v1/motivational/integration/status"
        ]
        
        missing_routes = []
        for expected_route in expected_routes:
            if expected_route not in routes:
                missing_routes.append(expected_route)
        
        if missing_routes:
            print(f"❌ Expected routes not found: {missing_routes}")
            print(f"   Available routes: {routes}")
            return False
        
        print("✅ FastAPI app created successfully with expected routes")
        print(f"   Total routes registered: {len(routes)}")
        return True
        
    except Exception as e:
        print(f"❌ FastAPI app creation failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing NYX FastAPI Application")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        sys.exit(1)
    
    print()
    
    # Test app creation
    if not test_app_creation():
        sys.exit(1)
    
    print()
    print("🎉 All basic tests passed!")
    print("FastAPI application is ready for testing")