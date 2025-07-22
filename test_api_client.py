#!/usr/bin/env python3
"""
NYX FastAPI Client Test

Simple test client to verify API endpoints are working correctly.
"""

import sys
import os
import asyncio
import httpx
import json
from typing import Dict, Any

# Add current directory to Python path  
sys.path.insert(0, os.path.abspath('.'))

BASE_URL = "http://localhost:8000"

class NYXAPIClient:
    """Simple client for testing NYX API endpoints"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        
    async def test_health_check(self) -> bool:
        """Test basic health check endpoint"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Health Check: {data['status']}")
                    return True
                else:
                    print(f"❌ Health Check failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Health Check error: {e}")
            return False
    
    async def test_system_status(self) -> bool:
        """Test system status endpoint"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/v1/system/status")
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ System Status: Database {data.get('database', {}).get('status', 'unknown')}")
                    return True
                else:
                    print(f"❌ System Status failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ System Status error: {e}")
            return False
    
    async def test_orchestrator_info(self) -> bool:
        """Test orchestrator information endpoints"""
        try:
            async with httpx.AsyncClient() as client:
                # Test strategies endpoint
                response = await client.get(f"{self.base_url}/api/v1/orchestrator/strategies")
                if response.status_code == 200:
                    data = response.json()
                    strategy_count = data.get('count', 0)
                    print(f"✅ Orchestrator Strategies: {strategy_count} available")
                else:
                    print(f"❌ Orchestrator Strategies failed: {response.status_code}")
                    return False
                
                # Test input types endpoint
                response = await client.get(f"{self.base_url}/api/v1/orchestrator/input-types")
                if response.status_code == 200:
                    data = response.json()
                    input_type_count = data.get('count', 0)
                    print(f"✅ Orchestrator Input Types: {input_type_count} available")
                    return True
                else:
                    print(f"❌ Orchestrator Input Types failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Orchestrator Info error: {e}")
            return False
    
    async def test_motivational_status(self) -> bool:
        """Test motivational engine status"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/v1/motivational/engine/status")
                if response.status_code == 200:
                    data = response.json()
                    running = data.get('running', False)
                    print(f"✅ Motivational Engine Status: {'Running' if running else 'Stopped'}")
                    return True
                else:
                    print(f"❌ Motivational Engine Status failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Motivational Engine Status error: {e}")
            return False
    
    async def test_workflow_execution(self) -> bool:
        """Test basic workflow execution (simple test)"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                workflow_request = {
                    "input_type": "user_prompt",
                    "content": {
                        "prompt": "This is a test workflow execution from the API client"
                    },
                    "priority": "medium",
                    "urgency": "normal"
                }
                
                print("🧪 Testing workflow execution (this may take a moment)...")
                response = await client.post(
                    f"{self.base_url}/api/v1/orchestrator/workflows/execute",
                    json=workflow_request
                )
                
                if response.status_code == 200:
                    data = response.json()
                    success = data.get('success', False)
                    execution_time = data.get('execution_time_ms', 0)
                    print(f"✅ Workflow Execution: Success={success}, Time={execution_time}ms")
                    return True
                else:
                    print(f"❌ Workflow Execution failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Workflow Execution error: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all API tests"""
        print("🧪 Testing NYX FastAPI Endpoints")
        print("=" * 50)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("System Status", self.test_system_status),
            ("Orchestrator Info", self.test_orchestrator_info),
            ("Motivational Status", self.test_motivational_status),
            ("Workflow Execution", self.test_workflow_execution)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🔍 Running {test_name}...")
            try:
                if await test_func():
                    passed += 1
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
        
        print(f"\n" + "=" * 50)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All API tests passed!")
            return True
        else:
            print(f"⚠️  {total - passed} tests failed")
            return False

async def main():
    """Main test runner"""
    client = NYXAPIClient()
    
    print("💡 Make sure NYX FastAPI server is running:")
    print("   python3 start_api.py")
    print("   or: uvicorn app.main:app --reload")
    print()
    
    success = await client.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)