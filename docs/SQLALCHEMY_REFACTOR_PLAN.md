# SQLAlchemy Session Boundary Refactor - Implementation Plan

## Overview
This document outlines the systematic refactoring plan to eliminate SQLAlchemy session boundary violations in NYX, based on comprehensive codebase audit findings.

## Current State Assessment
- **23 high-risk anti-patterns identified** across motivational system
- **Core issue**: Model objects passed across async session boundaries
- **Primary failure point**: `task.motivational_state.motivation_type` lazy loading
- **Impact**: Intermittent "greenlet_spawn" errors blocking autonomous operation

## Refactor Strategy

### Phase 1: Critical Path Fixes (Priority 1 - Immediate)

#### Target: Motivational Orchestrator Integration
**Files to modify:**
- `core/motivation/orchestrator_integration.py`
- `core/motivation/feedback.py` 
- `core/motivation/states.py`

#### 1.1 Create Data Transfer Objects

**File:** `core/motivation/dto.py` (NEW)
```python
@dataclass
class TaskSpawnContext:
    """Data context for spawning motivated workflows - replaces MotivationalTask object"""
    task_id: str
    generated_prompt: str
    motivation_type: str
    motivation_state_id: str
    task_priority: float
    arbitration_score: float
    status: str
    spawned_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass  
class WorkflowExecutionContext:
    """Context for workflow execution - replaces mixed object/primitive approach"""
    task_context: TaskSpawnContext
    thought_tree_id: str
    orchestrator_id: str
    started_at: datetime
    workflow_input: Dict[str, Any]
```

#### 1.2 Refactor Core Integration Methods

**Target method:** `_spawn_workflow_for_task()`
```python
# BEFORE (current anti-pattern)
async def _spawn_workflow_for_task(self, session, task: MotivationalTask):
    # Uses task.motivational_state.motivation_type - FAILS

# AFTER (correct pattern)
async def _spawn_workflow_for_task_data(self, task_context: TaskSpawnContext):
    # Uses task_context.motivation_type - SAFE
```

#### 1.3 Update Task Context Extraction

**Target location:** `_process_pending_tasks()` method
```python
# BEFORE
for task in pending_tasks:
    await self._spawn_workflow_for_task(session, task)

# AFTER  
for task in pending_tasks:
    task_context = await self._extract_task_context(session, task)
    await self._spawn_workflow_for_task_data(task_context)
```

**New method:** `_extract_task_context()`
```python
async def _extract_task_context(self, session: AsyncSession, task: MotivationalTask) -> TaskSpawnContext:
    """Extract all needed task data while session is active"""
    # Eager load motivational_state relationship
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    
    full_task = await session.execute(
        select(MotivationalTask)
        .options(selectinload(MotivationalTask.motivational_state))
        .where(MotivationalTask.id == task.id)
    )
    task_with_state = full_task.scalar_one()
    
    return TaskSpawnContext(
        task_id=str(task_with_state.id),
        generated_prompt=task_with_state.generated_prompt,
        motivation_type=task_with_state.motivational_state.motivation_type,
        motivation_state_id=str(task_with_state.motivational_state_id),
        task_priority=task_with_state.task_priority,
        arbitration_score=task_with_state.arbitration_score,
        status=task_with_state.status
    )
```

### Phase 2: Supporting Infrastructure (Priority 2)

#### 2.1 Update Method Signatures

**Files to modify:**
- `core/motivation/orchestrator_integration.py:208` - `_create_workflow_input_from_task()`
- `core/motivation/orchestrator_integration.py:259` - `_create_thought_tree_within_session()`
- `core/motivation/feedback.py:145` - Update all task.motivational_state accesses

#### 2.2 Workflow Info Storage Pattern

**Current problematic pattern:**
```python
workflow_info = {
    'motivation_type': task.motivational_state.motivation_type  # FAILS
}
```

**Correct pattern:**
```python
workflow_info = {
    'motivation_type': task_context.motivation_type  # SAFE
}
```

#### 2.3 Testing Infrastructure Updates

**Files to modify:**
- All test files that instantiate model objects across sessions
- Debug scripts to demonstrate correct patterns

### Phase 3: Architecture Hardening (Priority 3)

#### 3.1 Session Boundary Validation

**New utility:** `core/database/session_validator.py`
```python
def validate_session_boundary(obj: Any) -> None:
    """Development helper to detect session boundary violations"""
    if hasattr(obj, '_sa_instance_state'):
        state = obj._sa_instance_state
        if not state.session:
            raise RuntimeError(f"Detached SQLAlchemy object: {obj}")
```

#### 3.2 DTO Base Classes

**File:** `core/motivation/dto.py`
```python
@dataclass
class BaseContext:
    """Base class for all data transfer objects"""
    
    def validate(self) -> None:
        """Validate context data"""
        pass
    
    @classmethod
    def from_model(cls, model: Any, session: AsyncSession):
        """Factory method to create DTO from model within session"""
        raise NotImplementedError
```

## Implementation Order

### Week 1: Foundation
1. ✅ Create `core/motivation/dto.py` with data transfer objects
2. ✅ Implement `_extract_task_context()` method
3. ✅ Update `_spawn_workflow_for_task()` signature and implementation

### Week 2: Core Fixes  
1. ✅ Refactor `_create_workflow_input_from_task()` to use context
2. ✅ Fix workflow info storage patterns
3. ✅ Update all motivational_state lazy loading instances

### Week 3: Testing & Validation
1. ✅ Update integration tests to use new patterns
2. ✅ Run comprehensive test suite
3. ✅ Performance testing for eager loading impact

### Week 4: Documentation & Cleanup
1. ✅ Update documentation with new patterns
2. ✅ Clean up debug scripts
3. ✅ Add session boundary validation tooling

## Risk Mitigation

### Backward Compatibility
- Keep old methods temporarily with deprecation warnings
- Gradual migration approach
- Comprehensive testing at each stage

### Performance Considerations
- **Eager Loading**: `selectinload()` adds query complexity but eliminates N+1 patterns
- **Memory**: DTOs use slightly more memory but prevent session leaks
- **CPU**: Data extraction overhead minimal compared to session management costs

### Testing Strategy
- **Unit Tests**: Test DTOs with simple data, no database required
- **Integration Tests**: Test full workflow with real database
- **Performance Tests**: Measure eager loading vs lazy loading performance
- **Stress Tests**: Validate no session leaks under load

## Success Criteria

### Immediate (Phase 1)
- ✅ No more "greenlet_spawn" errors in integration tests
- ✅ All motivational integration tests pass
- ✅ Autonomous task generation working reliably

### Short-term (Phase 2)
- ✅ All SQLAlchemy anti-patterns eliminated from audit list
- ✅ Clean separation between database and business logic layers
- ✅ Improved test reliability and speed

### Long-term (Phase 3)
- ✅ Session boundary violations impossible by design
- ✅ Easy to add new motivational features without session issues
- ✅ Performance improvements from eliminated N+1 queries

## Code Review Checklist

Before merging any changes, verify:
- [ ] No SQLAlchemy model objects passed across async boundaries
- [ ] All relationship access happens within session context
- [ ] DTOs used for cross-module communication
- [ ] Tests pass without database session warnings
- [ ] Documentation updated with new patterns

## Rollback Plan

If issues arise:
1. **Immediate**: Revert to previous working commit
2. **Partial**: Keep DTOs, revert method signatures
3. **Full**: Complete rollback with post-mortem analysis

## Dependencies

### Internal
- Database layer (no changes required)
- Orchestrator system (minimal changes to workflow input handling)
- Agent system (no direct changes)

### External
- SQLAlchemy patterns remain compatible
- Async frameworks not affected
- Testing frameworks compatible with DTO pattern

## Monitoring

### Production Metrics
- Count of session boundary exceptions (target: 0)
- Memory usage of motivational system components
- Query performance for eager loading patterns

### Development Metrics  
- Time to write tests (should improve with DTOs)
- Debugging session issues (should decrease significantly)
- New feature development velocity (should improve)

This refactor represents a fundamental architectural improvement that will eliminate an entire class of runtime errors while improving code maintainability and testability.