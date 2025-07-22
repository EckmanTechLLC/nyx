# SQLAlchemy Async Patterns - NYX Architecture Guide

## Overview

This document establishes the architectural patterns for handling SQLAlchemy objects in NYX's async environment, specifically addressing session boundary management and preventing detached instance errors.

## Core Problem

**Issue**: SQLAlchemy ORM objects become "detached" when accessed outside their originating session context, causing runtime errors in async environments.

**Manifestation in NYX**: 
```python
# ❌ Anti-pattern that causes detached instance errors
async def process_task(task: MotivationalTask):
    # Session closed, task is now detached
    motivation_type = task.motivational_state.motivation_type  # FAILS!
```

## Architectural Solution: Data Transfer Pattern

### Principle
**Pass data structures, not ORM objects, across session boundaries.**

### Pattern Implementation

#### 1. Data Extraction at Session Boundary
```python
# ✅ Extract all needed data while session is active
async with db_manager.get_async_session() as session:
    task = await session.get(MotivationalTask, task_id)
    
    # Extract ALL needed data before session closes
    task_data = TaskSpawnContext(
        task_id=str(task.id),
        generated_prompt=task.generated_prompt,
        motivation_type=task.motivational_state.motivation_type,  # OK - session active
        priority=task.task_priority,
        arbitration_score=task.arbitration_score
    )
    await session.commit()

# ✅ Pass data structure, not ORM object
await process_task_data(task_data)
```

#### 2. Data Transfer Objects (DTOs)
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class TaskSpawnContext:
    """Data context for spawning motivated workflows"""
    task_id: str
    generated_prompt: str
    motivation_type: str
    priority: float
    arbitration_score: float
    metadata: Optional[Dict[str, Any]] = None
```

#### 3. Function Signatures
```python
# ❌ Anti-pattern - requires active session
async def spawn_workflow(task: MotivationalTask):
    pass

# ✅ Correct pattern - explicit data dependencies  
async def spawn_workflow(task_context: TaskSpawnContext):
    pass
```

## Implementation Guidelines

### Rule 1: Session Boundaries Are Data Boundaries
- Never pass SQLAlchemy objects across `async with session:` boundaries
- Extract all needed data before session closure
- Use data classes/dictionaries for cross-boundary communication

### Rule 2: Eager Loading Strategy
```python
# ✅ Load relationships while session is active
from sqlalchemy.orm import selectinload

task = await session.execute(
    select(MotivationalTask)
    .options(selectinload(MotivationalTask.motivational_state))
    .where(MotivationalTask.id == task_id)
)
```

### Rule 3: Explicit Dependencies
- Make data requirements explicit in function signatures
- Document what data each component needs
- Fail fast with clear error messages

### Rule 4: Testing Pattern
```python
# ✅ Easy to test with data structures
def test_workflow_spawn():
    task_data = TaskSpawnContext(
        task_id="test-id",
        generated_prompt="test prompt",
        motivation_type="test_motivation"
    )
    result = await spawn_workflow(task_data)
    assert result.success
```

## Migration Strategy

### Phase 1: Identify Anti-patterns
Search for:
- Functions accepting SQLAlchemy model objects
- Cross-session object access
- Lazy loading outside session contexts

### Phase 2: Create Data Transfer Objects
- Define DTOs for each use case
- Include all necessary data fields
- Add validation and type hints

### Phase 3: Update Function Signatures
- Change parameters from model objects to DTOs
- Update all calling code
- Add comprehensive tests

### Phase 4: Validation
- Run integration tests
- Monitor for detached instance errors
- Performance testing

## Common Patterns in NYX

### Motivational System
```python
# Before: Pass task object
await integration._spawn_workflow_for_task(session, task)

# After: Pass task data  
task_context = extract_task_context(session, task)
await integration._spawn_workflow_for_task_data(task_context)
```

### Orchestrator Integration
```python
# Before: Access relationships later
workflow_info = {
    'motivation_type': task.motivational_state.motivation_type  # FAILS
}

# After: Include in context
workflow_info = {
    'motivation_type': task_context.motivation_type  # SUCCESS
}
```

## Benefits

1. **Reliability**: Eliminates detached instance errors
2. **Testability**: Easy to unit test with simple data structures  
3. **Maintainability**: Explicit dependencies and clear interfaces
4. **Performance**: No unexpected lazy loading queries
5. **Scalability**: Works well with connection pooling and distributed systems

## Anti-patterns to Avoid

### ❌ Session Extension
```python
# Don't try to keep sessions alive longer
session = db_manager.get_async_session()
result = await long_running_operation(session, task)
await session.close()  # Dangerous
```

### ❌ Object Reattachment  
```python
# Don't try to reattach objects to new sessions
new_session.merge(detached_task)  # Complex and error-prone
```

### ❌ Lazy Loading Assumptions
```python
# Don't assume relationships will be available
if task.motivational_state:  # May trigger lazy load and fail
    pass
```

## Conclusion

This pattern trades a small amount of boilerplate (data extraction) for significant improvements in reliability, testability, and maintainability. It aligns with async best practices and prevents an entire class of runtime errors.

**Remember**: In async SQLAlchemy, session boundaries are data boundaries. Respect them.