# Security Tests for Two-Phase Thread Persistence

## Summary of Changes

This commit fixes **3 CRITICAL SECURITY BUGS** and corrects documentation assumptions:

### 1. **FIXED: get_thread_author() Security Hole**
   - **Before:** Returned "system" or userId for pending/missing threads
   - **After:** Returns `None` for pending or non-existent threads
   - **Impact:** Prevents unauthorized access to threads without user context

### 2. **FIXED: list_threads() Cross-User Data Leak**
   - **Before:** No user filtering - all users could see all threads
   - **After:** Filters by `filters.userId` - users only see their own threads
   - **Impact:** Prevents cross-user data leaks in multi-tenant environments

### 3. **FIXED: Documentation False Assumption**
   - **Before:** Docs/tests claimed "pending threads must be 0 always"
   - **After:** Corrected to "pending threads are transient and hidden from users"
   - **Impact:** Realistic production expectations + cleanup strategy

### 4. **ADDED: Production-Grade Automated Tests**
   - 7 pytest tests covering all security invariants
   - Tests use isolated temp SQLite databases
   - All tests pass ✅

## Running Tests

### Prerequisites
```bash
py -m pip install pytest pytest-asyncio
```

### Run Security Tests
```bash
# Run all security tests
py -m pytest tests/test_thread_security.py -v -s

# Run specific test
py -m pytest tests/test_thread_security.py::test_get_thread_author_pending_returns_none -v

# Quick run (no verbose)
py -m pytest tests/test_thread_security.py -q
```

### Run Manual Verification (Legacy)
```bash
py test_thread_persistence.py
```

## Test Coverage

### Security Invariants Tested

1. ✅ **test_get_thread_author_missing_returns_none**
   - Verifies `get_thread_author()` returns `None` for non-existent threads

2. ✅ **test_get_thread_author_pending_returns_none**
   - Verifies `get_thread_author()` returns `None` for pending threads (no user context)

3. ✅ **test_get_thread_author_completed_returns_identifier**
   - Verifies `get_thread_author()` returns `userIdentifier` for complete threads

4. ✅ **test_list_threads_filters_by_user**
   - Verifies users only see their own threads (no cross-user leaks)
   - Creates 2 users (Alice, Bob) with separate threads
   - Confirms Alice cannot see Bob's threads and vice versa

5. ✅ **test_list_threads_hides_pending**
   - Verifies pending threads never appear in sidebar
   - Even if they exist in DB

6. ✅ **test_get_thread_blocks_pending**
   - Verifies `get_thread()` returns `None` for pending threads
   - Blocks resume functionality for incomplete threads

7. ✅ **test_two_phase_flow_persists_steps_and_finalizes**
   - End-to-end test of two-phase model
   - Phase A: `create_step()` creates pending thread
   - Phase B: `update_thread()` finalizes with user data
   - Verifies security checks work at each phase

## Expected Output

```
============================= test session starts =============================
collected 7 items

tests/test_thread_security.py::test_get_thread_author_missing_returns_none PASSED
tests/test_thread_security.py::test_get_thread_author_pending_returns_none PASSED
tests/test_thread_security.py::test_get_thread_author_completed_returns_identifier PASSED
tests/test_thread_security.py::test_list_threads_filters_by_user PASSED
tests/test_thread_security.py::test_list_threads_hides_pending PASSED
tests/test_thread_security.py::test_get_thread_blocks_pending PASSED
tests/test_thread_security.py::test_two_phase_flow_persists_steps_and_finalizes PASSED

======================= 7 passed in 1.50s ========================
```

## Files Modified

- `app/ui/data_layer.py`
  - Fixed `get_thread_author()` to return `None` for pending/missing
  - Fixed `list_threads()` to filter by `userId`
  
- `THREAD_PERSISTENCE.md`
  - Corrected pending thread semantics
  - Added cleanup strategy for orphaned pending threads

- `test_thread_persistence.py`
  - Removed false "pending must be 0" assertion
  - Updated to reflect transient pending state

- `tests/test_thread_security.py` (NEW)
  - 7 automated pytest tests
  - Isolated temp DB per test
  - Full coverage of security invariants

## Acceptance Criteria ✅

- [x] No "silent skip" in create_step (nema retry+skip)
- [x] get_thread_author ne može vratiti autora za pending
- [x] list_threads nikad ne vraća pending niti tuđe threade
- [x] Dokumentacija više ne tvrdi "pending mora biti 0 uvijek"
- [x] Testovi prolaze (7/7 PASSED)

## Production Deployment

Before deploying:

1. Run tests: `py -m pytest tests/test_thread_security.py -v`
2. Verify all pass
3. Optional: Add cleanup job for old pending threads:
   ```python
   # In startup script or periodic task
   DELETE FROM threads 
   WHERE (userId IS NULL OR userIdentifier IS NULL) 
     AND datetime(createdAt) < datetime('now', '-24 hours');
   ```

## Questions?

See `THREAD_PERSISTENCE.md` for full documentation on two-phase model.

