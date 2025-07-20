# SQLAlchemy Query Pattern Fixes Applied

## Issue Fixed
The learning system modules were using the older `session.query()` pattern which is not available on AsyncSession objects in SQLAlchemy 2.x. Your codebase uses the modern `session.execute(select(...))` pattern.

## Files Fixed

### 1. **core/learning/metrics.py**
- Added `select` import
- Fixed 5 instances of `session.query()` → `session.execute(select())`
- Lines: 90, 98, 105, 339, 378

### 2. **core/learning/scorer.py** 
- Added `select` import
- Fixed 3 instances of `session.query()` → `session.execute(select())`
- Lines: 194, 203, 252

### 3. **core/learning/patterns.py**
- Added `select` import  
- Fixed 6 instances of `session.query()` → `session.execute(select())`
- Lines: 129, 214, 361, 458, 474, 570

### 4. **tests/scripts/test_scoring_system.py**
- Added `select` import
- Fixed 1 instance in cleanup code
- Line: 412

### 5. **tests/scripts/test_learning_system.py**
- Added `select` import
- Fixed 1 instance in cleanup code  
- Line: 475

## Total Changes
- **16 instances** of `session.query()` converted to `session.execute(select())`
- **5 files** updated with consistent SQLAlchemy 2.x async patterns
- **All imports** updated to include `select` from sqlalchemy

## Result
The learning system now uses the same modern SQLAlchemy patterns as the rest of your codebase. This should resolve the `'AsyncSession' object has no attribute 'query'` errors.

## Test Files Ready
Both test files are now fixed and ready to run:
- `python tests/scripts/test_scoring_system.py` 
- `python tests/scripts/test_learning_system.py`