# Security Tests for Two-Phase Thread Persistence

## Summary of Changes

### Previous Security Fixes (Commit 1)
This commit fixed **3 CRITICAL SECURITY BUGS** and corrected documentation assumptions:

1. **FIXED: get_thread_author() Security Hole**
   - Returns `None` for pending or non-existent threads
   - Prevents unauthorized access to threads without user context

2. **FIXED: list_threads() Cross-User Data Leak**
   - Filters by `filters.userId` - users only see their own threads
   - Prevents cross-user data leaks in multi-tenant environments

3. **FIXED: Documentation False Assumption**
   - Corrected to "pending threads are transient and hidden from users"
   - Realistic production expectations + cleanup strategy

### Current Production-Grade Improvements (Commit 2)

This commit adds **3 PRODUCTION-GRADE IMPROVEMENTS** to the two-phase model:

### 1. **FAIL-CLOSED list_threads()**
   - **Before:** If `filters.userId` missing → returned all complete threads (potential leak)
   - **After:** If `filters.userId` missing → returns empty list (fail-closed)
   - **Impact:** Safe default prevents accidental data leaks
   - **Dev bypass:** Set `DEV_ADMIN_BYPASS=1` env var for dev/admin access (⚠️ NEVER in production)

### 2. **FLEXIBLE userId/userIdentifier Filtering**
   - **Before:** Only filtered by `userId = ?`
   - **After:** Filters by `userId = ? OR userIdentifier = ?`
   - **Impact:** Works with both UUID and identifier string (e.g., "admin")
   - **Chainlit compatibility:** Handles both filter formats

### 3. **SAFE STEP UPSERT (Data Quality)**
   - **Before:** `INSERT OR REPLACE` (DELETE+INSERT) NULLed out other columns
   - **After:** `INSERT ... ON CONFLICT DO UPDATE` preserves existing columns
   - **Impact:** Prevents data loss for step fields like `start`, `end`, `generation`

### 4. **ADDED: 2 New Automated Tests**
   - Total: 9 pytest tests covering all security invariants
   - Tests use isolated temp SQLite databases
   - All tests pass ✅ (9/9)

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

### Security Invariants Tested (9 tests total)

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

8. ✅ **test_list_threads_fail_closed_without_user_filter** (NEW)
   - Verifies `list_threads()` returns empty list when no userId filter
   - Tests both `None` and empty string cases
   - Fail-closed security posture

9. ✅ **test_list_threads_filters_by_userid_or_identifier** (NEW)
   - Verifies `list_threads()` works with both UUID and identifier string
   - Creates users with UUIDs and identifiers ("admin", "bob")
   - Tests filtering by identifier string → returns correct thread
   - Tests filtering by UUID → returns correct thread
   - Confirms OR logic works correctly

## Expected Output

```
============================= test session starts =============================
collected 9 items

tests/test_thread_security.py::test_get_thread_author_missing_returns_none PASSED
tests/test_thread_security.py::test_get_thread_author_pending_returns_none PASSED
tests/test_thread_security.py::test_get_thread_author_completed_returns_identifier PASSED
tests/test_thread_security.py::test_list_threads_filters_by_user PASSED
tests/test_thread_security.py::test_list_threads_hides_pending PASSED
tests/test_thread_security.py::test_get_thread_blocks_pending PASSED
tests/test_thread_security.py::test_two_phase_flow_persists_steps_and_finalizes PASSED
tests/test_thread_security.py::test_list_threads_fail_closed_without_user_filter PASSED
tests/test_thread_security.py::test_list_threads_filters_by_userid_or_identifier PASSED

======================= 9 passed in 1.56s ========================
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

### Commit 1 (Previous)
- [x] No "silent skip" in create_step (nema retry+skip)
- [x] get_thread_author ne može vratiti autora za pending
- [x] list_threads nikad ne vraća pending niti tuđe threade
- [x] Dokumentacija više ne tvrdi "pending mora biti 0 uvijek"

### Commit 2 (Current)
- [x] list_threads is fail-closed (returns empty without user filter)
- [x] list_threads supports userId OR userIdentifier filtering
- [x] create_step uses safe UPSERT (no data loss)
- [x] All tests pass (9/9 PASSED)

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

