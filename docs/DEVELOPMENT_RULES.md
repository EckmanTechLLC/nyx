# NYX Development Rules

## Test Script Development

### Location and Naming
- **Location**: All test scripts MUST be placed in `tests/scripts/`
- **Naming**: Use descriptive names like `test_cache_hit.py`, `test_api_integration.py`
- **Executable**: Scripts should be executable with `python tests/scripts/script_name.py`

### Test Script Requirements

#### 1. NO Hardcoded Success Messages
❌ **WRONG - Hardcoded success:**
```python
# BAD: This prints success even when test fails
if some_condition:
    print("🎉 SUCCESS: Test passed!")
    return True
else:
    print("❌ Test failed")
    return False
```

✅ **CORRECT - Conditional success:**
```python
# GOOD: Success only printed when test actually passes
actual_cache_hits = stats.get('cache_hits', 0) > 0
cost_savings = stats.get('cost_saved', 0) > 0

if actual_cache_hits and cost_savings:
    print("🎉 SUCCESS: Cache is working with real savings!")
    return True
else:
    print("❌ FAILED: No actual cache hits or savings detected")
    return False
```

#### 2. Real Failure Detection
- Test scripts must verify ACTUAL functionality, not just API responses
- Use real data to determine success/failure
- Provide specific failure reasons when tests fail

#### 3. Proper Error Handling
```python
async def main():
    try:
        success = await run_test()
        return success
    except Exception as e:
        print(f"💥 Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
```

#### 4. Clear Output Format
```python
print("🔍 TESTING [FEATURE_NAME]")
print("=" * 50)

# Test steps with clear indicators
print("📞 Call 1: Creating cache...")
print("📞 Call 2: Testing cache hit...")

print("📊 RESULTS:")
print(f"   Actual metric: {actual_value}")
print(f"   Expected: {expected_value}")

# Final result based on real data
if test_passes_real_checks:
    print("✅ SUCCESS: All checks passed")
else:
    print("❌ FAILED: Specific reason for failure")
```

## Code Development

### LLM Integration Rules
- Always use `llm/claude_native.py` for Claude API calls
- Use real API response data for cache detection
- Never fake or simulate cache hits in production code
- Log all interactions to database with complete metadata

### Database Integration
- Use async database sessions
- Log failures gracefully without breaking main flow
- Include all relevant metadata fields

### Error Handling
- Implement proper retry logic with exponential backoff
- Use circuit breaker pattern for API failures
- Provide meaningful error messages with context

## File Organization

### Directory Structure
```
llm/
├── models.py           # Data structures and cost calculations
├── claude_native.py    # Main Claude API wrapper with native caching
├── native_cache.py     # Cache management and statistics
└── prompt_templates.py # Template management (to implement)

tests/scripts/
├── test_cache_hit.py           # Cache functionality tests
├── test_real_cache_detection.py # API response validation
└── debug_cache_api.py          # Debug tools
```

### Import Conventions
```python
# Standard imports first
import asyncio
import sys
from pathlib import Path

# Add project root to path for scripts
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Project imports
from llm.claude_native import ClaudeNativeAPI
from llm.models import LLMModel
```

## Testing Philosophy ⚠️ **CRITICAL SAFETY UPDATE**

### Container Isolation Requirements **MANDATORY**
- 🐳 **ALL TESTS MUST RUN IN DOCKER CONTAINERS** - Never execute tests directly on development host
- 🚫 **NYX EXECUTION PROHIBITED OUTSIDE CONTAINERS** - Assistant is NEVER allowed to execute or initiate NYX
- 🔒 **Container isolation mandatory** - NYX's growing autonomy and capabilities require strict containment
- 🛡️ **Safety First** - As NYX gains motivational models and autonomous behavior, containerization is essential

### Test What Matters
- ✅ Test actual functionality and performance
- ✅ Verify real cost savings and cache hits
- ✅ Check database logging completeness
- ❌ Don't test fake/simulated behavior
- ❌ Don't hardcode success messages

### User Runs Tests (Container-Only)
- Developers create test scripts following these rules
- Users run tests **ONLY within Docker containers** to verify functionality
- Test output must be clear and actionable
- Failures must provide specific debugging information
- **ALL NYX execution must be containerized for safety**

## Documentation
- Update documentation when functionality changes
- Include working code examples
- Document any breaking changes
- Keep status indicators current (✅ OPERATIONAL, ❌ TO IMPLEMENT)