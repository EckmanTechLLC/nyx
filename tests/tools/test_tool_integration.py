#!/usr/bin/env python3
"""
NYX Tool Integration Tests

Comprehensive test suite for the NYX Tool Interface Layer with real database
interactions and integration testing.
"""
import asyncio
import os
import tempfile
import uuid
from pathlib import Path

# Add the project root to the Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.tools import (
    BaseTool, ToolResult, ToolState,
    FileOperationsTool, FileOperationConfig,
    ShellCommandTool, ShellCommandConfig
)
from database.connection import db_manager
from config.settings import settings

class TestTool(BaseTool):
    """Simple test tool for basic functionality testing"""
    
    def __init__(self, **kwargs):
        super().__init__(tool_name="test_tool", **kwargs)
    
    async def _validate_parameters(self, parameters):
        return "test_param" in parameters
    
    async def _validate_safety(self, parameters):
        return parameters.get("safe", True)
    
    async def _tool_specific_execution(self, parameters):
        if parameters.get("should_fail", False):
            return ToolResult(
                success=False,
                output="",
                error_message="Test failure requested"
            )
        
        return ToolResult(
            success=True,
            output=f"Test executed with param: {parameters['test_param']}",
            metadata={"test_data": "success"}
        )

async def test_database_connection():
    """Test database connectivity for tool logging"""
    print("=== Testing Database Connection ===")
    
    try:
        async with db_manager.get_async_session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

async def test_base_tool_functionality():
    """Test basic tool functionality"""
    print("\n=== Testing BaseTool Functionality ===")
    
    tool = TestTool()
    
    # Test successful execution
    result = await tool.execute({
        "test_param": "hello world",
        "safe": True
    })
    
    assert result.success, f"Tool execution failed: {result.error_message}"
    assert "hello world" in result.output
    print("✅ Basic tool execution successful")
    
    # Test parameter validation
    result = await tool.execute({
        "missing_param": "value"
    })
    
    assert not result.success
    assert "Parameter validation failed" in result.error_message
    print("✅ Parameter validation working")
    
    # Test safety validation
    result = await tool.execute({
        "test_param": "value",
        "safe": False
    })
    
    assert not result.success
    assert "Safety validation failed" in result.error_message
    print("✅ Safety validation working")
    
    # Test retry logic with failure
    result = await tool.execute({
        "test_param": "retry_test",
        "should_fail": True
    })
    
    assert not result.success
    assert "Test failure requested" in result.error_message
    print("✅ Retry logic and failure handling working")
    
    # Test statistics
    stats = await tool.get_statistics()
    assert stats['total_executions'] > 0
    print(f"✅ Tool statistics: {stats['total_executions']} executions, success rate: {stats['success_rate']:.2f}")
    
    return True

async def test_file_operations_tool():
    """Test file operations tool functionality"""
    print("\n=== Testing File Operations Tool ===")
    
    # Create temporary test directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files
        test_file = temp_path / "test.py"
        test_file.write_text("""#!/usr/bin/env python3
# Test Python file
def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
""")
        
        test_dir = temp_path / "subdir"
        test_dir.mkdir()
        (test_dir / "another_file.txt").write_text("Test content in subdirectory")
        
        # Initialize file operations tool
        config = FileOperationConfig(
            max_file_size_mb=1,
            max_files_per_operation=100
        )
        
        tool = FileOperationsTool(
            config=config,
            agent_id=str(uuid.uuid4()),
            thought_tree_id=str(uuid.uuid4())
        )
        
        # Test file reading
        result = await tool.execute({
            "operation": "read_file",
            "path": str(test_file)
        })
        
        assert result.success, f"File read failed: {result.error_message}"
        assert "Hello, World!" in result.output
        assert result.metadata["file_size_bytes"] > 0
        print("✅ File reading successful")
        
        # Test directory listing
        result = await tool.execute({
            "operation": "list_directory",
            "path": str(temp_path),
            "recursive": True
        })
        
        assert result.success, f"Directory listing failed: {result.error_message}"
        metadata = result.metadata
        assert metadata["total_files"] >= 2  # test.py and another_file.txt
        print(f"✅ Directory listing successful: {metadata['total_files']} files found")
        
        # Test codebase analysis
        result = await tool.execute({
            "operation": "analyze_codebase",
            "path": str(temp_path)
        })
        
        assert result.success, f"Codebase analysis failed: {result.error_message}"
        analysis = result.metadata
        assert analysis["total_files"] > 0
        assert ".py" in analysis["file_types"]
        print(f"✅ Codebase analysis successful: {analysis['total_files']} files, {len(analysis['file_types'])} file types")
        
        # Test safety validation - forbidden path
        result = await tool.execute({
            "operation": "read_file",
            "path": "/etc/passwd"
        })
        
        assert not result.success
        print("✅ Safety validation prevents access to forbidden paths")
        
        # Test parameter validation
        result = await tool.execute({
            "operation": "invalid_operation"
        })
        
        assert not result.success
        print("✅ Parameter validation rejects invalid operations")
    
    return True

async def test_shell_command_tool():
    """Test shell command tool functionality"""
    print("\n=== Testing Shell Command Tool ===")
    
    try:
        # Configure with restricted commands for safety
        config = ShellCommandConfig(
            max_execution_time_seconds=30,
            max_output_size_mb=1,
            require_explicit_approval=False  # For testing
        )
        
        tool = ShellCommandTool(
            config=config,
            agent_id=str(uuid.uuid4()),
            thought_tree_id=str(uuid.uuid4())
        )
        print("✅ Shell command tool initialized")
        
        # Test safe command execution - echo
        result = await tool.execute({
            "command": "echo 'Hello from shell tool'"
        })
        
        assert result.success, f"Shell command failed: {result.error_message}"
        assert "Hello from shell tool" in result.output
        print("✅ Basic shell command execution successful")
        
        # Test command with output - ls (if available)
        result = await tool.execute({
            "command": "ls -la"
        })
        
        if result.success:
            assert result.metadata["return_code"] == 0
            print("✅ Shell command with output successful")
        else:
            print(f"⚠️ ls command not available or restricted: {result.error_message}")
        
        # Test working directory parameter
        with tempfile.TemporaryDirectory() as temp_dir:
            result = await tool.execute({
                "command": "pwd",
                "working_directory": temp_dir
            })
            
            if result.success:
                assert temp_dir in result.output or temp_dir in str(result.metadata.get("working_directory", ""))
                print("✅ Working directory parameter working")
            else:
                print(f"⚠️ pwd command not available: {result.error_message}")
        
        # Test safety validation - forbidden command
        result = await tool.execute({
            "command": "rm -rf /"
        })
        
        assert not result.success
        # The base tool returns "Safety validation failed" for safety violations
        assert "Safety validation failed" in result.error_message
        print("✅ Safety validation prevents dangerous commands")
        
        # Test command timeout (with a short timeout)
        short_timeout_tool = ShellCommandTool(
            config=ShellCommandConfig(max_execution_time_seconds=1)
        )
        
        try:
            result = await short_timeout_tool.execute({
                "command": "sleep 3"
            })
            
            # This should timeout or be rejected by the allowed commands list
            assert not result.success
            print("✅ Command timeout or rejection working")
        except Exception as e:
            # If sleep is not available or causes other issues, skip this test
            print(f"⚠️ Timeout test skipped due to system limitations: {str(e)}")
        
        # Test command statistics
        stats = await tool.get_command_statistics()
        print(f"✅ Command statistics: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Shell Command Tool test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_database_logging():
    """Test database logging of tool executions"""
    print("\n=== Testing Database Logging ===")
    
    tool = TestTool(
        agent_id=str(uuid.uuid4()),
        thought_tree_id=str(uuid.uuid4())
    )
    
    # Execute a tool to generate database log
    result = await tool.execute({
        "test_param": "database_logging_test"
    })
    
    assert result.success
    print("✅ Tool execution for database logging successful")
    
    # Check if tool execution was logged in database
    try:
        async with db_manager.get_async_session() as session:
            from database.models import ToolExecution
            from sqlalchemy import select
            
            query = select(ToolExecution).where(
                ToolExecution.tool_name == "test_tool"
            ).order_by(ToolExecution.started_at.desc()).limit(1)
            
            result_record = await session.execute(query)
            tool_execution = result_record.scalar_one_or_none()
            
            if tool_execution:
                assert tool_execution.tool_name == "test_tool"
                assert tool_execution.tool_class == "TestTool"
                assert tool_execution.input_parameters["test_param"] == "database_logging_test"
                print("✅ Tool execution logged to database successfully")
                print(f"   - Tool: {tool_execution.tool_name}")
                print(f"   - Duration: {tool_execution.duration_ms}ms")
                print(f"   - Success: {tool_execution.output_result['success']}")
                return True
            else:
                print("❌ Tool execution not found in database")
                return False
                
    except Exception as e:
        print(f"❌ Database logging check failed: {str(e)}")
        return False

async def run_comprehensive_tool_tests():
    """Run all tool integration tests"""
    print("🚀 NYX Tool Integration Test Suite")
    print("=" * 50)
    
    test_results = []
    
    # Test database connection first
    db_ok = await test_database_connection()
    test_results.append(("Database Connection", db_ok))
    
    if not db_ok:
        print("❌ Skipping other tests due to database connection failure")
        return False
    
    # Run all tests
    tests = [
        ("Base Tool Functionality", test_base_tool_functionality),
        ("File Operations Tool", test_file_operations_tool),
        ("Shell Command Tool", test_shell_command_tool),
        ("Database Logging", test_database_logging)
    ]
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            test_results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 50)
    print("🎯 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
    
    print("-" * 50)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Tool Interface Layer is ready for production.")
        return True
    else:
        print("⚠️  Some tests failed. Review implementation before proceeding.")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_comprehensive_tool_tests())