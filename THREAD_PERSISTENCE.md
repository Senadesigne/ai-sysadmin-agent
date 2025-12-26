# Thread Persistence & Two-Phase Creation

## Overview

This Chainlit starter kit implements a **TWO-PHASE thread creation model** to ensure deterministic thread persistence without data loss or security leaks.

## Problem

Chainlit's data layer may receive `create_step()` calls **before** `create_thread()` or `update_thread()` calls. This race condition can cause:
- Steps to be silently skipped (lost data)
- Threads to never be created (no sidebar entry)
- Resume failures ("Thread not found")

## Solution: Two-Phase Model

### Phase A: Minimal Thread Ensuring (`create_step`)

When `create_step()` is called for a non-existent thread:
1. Create a **pending thread** with minimal data:
   - `id`: thread UUID
   - `createdAt`: current timestamp
   - `name`: NULL
   - `userId`: NULL
   - `userIdentifier`: NULL
   - `tags`: []
   - `metadata`: {}

2. Insert step normally (thread guaranteed to exist)

**Key:** Uses `INSERT OR IGNORE` to be idempotent - won't fail if thread already exists.

### Phase B: User Data Population (`update_thread`)

When `update_thread()` is called with user data:
1. Check if thread exists
2. If **doesn't exist**: Create thread with full data (fallback, shouldn't happen)
3. If **exists**: Update only provided fields (partial update)
4. Resolve `userIdentifier` from `userId` automatically

**Key:** Uses UPSERT pattern - creates OR updates as needed.

## Security Features

### Pending Thread Filtering

Pending threads (without `userId` or `userIdentifier`) are **never shown to users**:

- **`list_threads()`**: Filters out threads where `userId IS NULL OR userIdentifier IS NULL`
- **`get_thread()`**: Returns `None` for pending threads (prevents resume)

This prevents:
- Orphaned threads appearing in sidebar
- Permission leaks (resuming threads without ownership)
- Data leaks (viewing threads without user context)

### Fail-Closed List Threads

**`list_threads()` is fail-closed** - if no user filter is provided, it returns an empty list:

- Without `filters.userId` → returns 0 threads (safe default)
- With `filters.userId` → filters by `userId = ? OR userIdentifier = ?`
- Supports both UUID (e.g., `user-123-uuid`) and identifier string (e.g., `"admin"`)
- Dev/admin bypass: Set `DEV_ADMIN_BYPASS=1` env var to show all threads (dev only)

This prevents:
- Accidental data leaks when user context is missing
- Cross-user data access in multi-tenant environments
- Default-open security posture (fail-closed is production-safe)

## Code Architecture

### Helper Functions

```python
async def _ensure_thread_exists(self, thread_id: str, db) -> None:
    """Phase A: Ensure minimal thread row exists"""
    await db.execute(
        """INSERT OR IGNORE INTO threads (id, createdAt, name, userId, userIdentifier, tags, metadata)
           VALUES (?, ?, NULL, NULL, NULL, '[]', '{}')""",
        (thread_id, datetime.utcnow().isoformat())
    )

async def _resolve_user_identifier(self, user_id: str) -> Optional[str]:
    """Resolve userIdentifier from userId"""
    # Queries users table and returns identifier
```

### Flow Diagram

```
User sends message
    ↓
Chainlit on_chat_start
    ↓
create_step(on_chat_start) ──→ Phase A: _ensure_thread_exists()
    ↓                                    ↓
create_step(assistant_msg)              INSERT OR IGNORE (pending thread)
    ↓                                    ↓
update_thread(name, userId) ────→ Phase B: UPSERT
    ↓                                    ↓
create_step(user_message)               UPDATE name, userId, userIdentifier
    ↓
Thread now complete in DB
    ↓
list_threads() shows thread in sidebar
```

## Manual Testing

### Test 1: New Chat Creation

1. Start the app: `./start.bat` or `python main.py`
2. Login as admin/admin
3. Create new chat
4. Send message: "test 123"
5. **Expected:**
   - Thread appears in sidebar with name "test 123"
   - No "Auto-created" or orphan threads
6. **Verify in DB:**
   ```python
   import sqlite3
   conn = sqlite3.connect('chainlit.db')
   cursor = conn.cursor()
   cursor.execute("SELECT id, name, userId, userIdentifier FROM threads ORDER BY createdAt DESC LIMIT 1")
   print(cursor.fetchone())
   # Should show: ('thread-id', 'test 123', 'user-uuid', 'admin')
   ```

### Test 2: Thread Resume After Refresh

1. After Test 1, refresh browser (F5)
2. Click on "test 123" thread in sidebar
3. **Expected:**
   - Thread loads successfully
   - All previous messages visible
   - Can continue conversation

### Test 3: Pending Threads Are Hidden

1. Run Test 1
2. **Verify in DB:**
   ```python
   cursor.execute("SELECT COUNT(*) FROM threads WHERE userId IS NULL OR userIdentifier IS NULL")
   print(cursor.fetchone())
   # May show pending threads (transient state) - this is OK
   # Pending threads exist briefly between create_step and update_thread
   # They are hidden from sidebar and cannot be resumed (security)
   ```
3. Check sidebar - should show only complete threads (pending filtered out)

### Test 4: Multiple Concurrent Chats

1. Open two browser tabs
2. Create chat in Tab 1: "chat A"
3. Create chat in Tab 2: "chat B"
4. Send messages in both
5. **Expected:**
   - Both threads appear in sidebar
   - No duplicate or orphan threads
   - Both can be resumed

## Debugging

Enable detailed logging by checking terminal output:

```
[DB] ENTER create_step threadId=xxx, type=run, name=on_chat_start
[DB] _ensure_thread_exists: thread xxx ensured (pending state)
[DB] EXIT create_step threadId=xxx
[DB] ENTER update_thread threadId=xxx, name=test 123, userId=yyy
[DB] EXIT update_thread threadId=xxx
```

If you see:
- `WARNING: create_step called for missing thread` - **should NOT happen** after this fix
- Threads with NULL userId in sidebar - **security bug**, report immediately

## Migration Notes

If upgrading from previous version:

1. No schema changes required
2. Existing threads remain unchanged
3. Old "Auto-created" threads can be cleaned up:
   ```sql
   DELETE FROM threads WHERE name = 'Auto-created' OR (userId IS NULL AND userIdentifier IS NULL);
   ```

## Production Checklist

- [x] Deterministic thread creation (no race conditions)
- [x] No silent step skipping (all data persisted)
- [x] Security filtering (pending threads hidden from sidebar)
- [x] Resume protection (get_thread returns None for pending)
- [x] Author check (get_thread_author returns None for pending)
- [x] User isolation (list_threads filters by userId OR userIdentifier)
- [x] Fail-closed list_threads (returns empty without user filter)
- [x] Safe step UPSERT (preserves existing columns, no data loss)
- [x] Idempotent operations (INSERT OR IGNORE for threads)
- [x] Partial updates (don't overwrite with NULL)
- [x] Clean logging (traceable flow)

## Pending Thread Semantics

**Expected Behavior:**
- Pending threads (userId=NULL or userIdentifier=NULL) may exist temporarily
- Created by `create_step()` before `update_thread()` is called
- Hidden from sidebar via `list_threads()` filter
- Blocked from resume via `get_thread()` returning None
- Blocked from author check via `get_thread_author()` returning None

**Cleanup Strategy (Optional):**
If app crashes between Phase A and Phase B, pending threads may accumulate:
```sql
-- Purge pending threads older than 24 hours
DELETE FROM threads 
WHERE (userId IS NULL OR userIdentifier IS NULL) 
  AND datetime(createdAt) < datetime('now', '-24 hours');
```
Run this on startup or periodically as maintenance task.

## Data Quality: Safe Step UPSERT

**`create_step()` uses safe UPSERT instead of INSERT OR REPLACE:**

- **Before:** `INSERT OR REPLACE` (SQLite DELETE+INSERT) would NULL out columns not in INSERT
- **After:** `INSERT ... ON CONFLICT(id) DO UPDATE SET ...` preserves existing columns
- **Impact:** Prevents data loss for step fields like `start`, `end`, `generation`, etc.

Example: If `update_step()` sets `start` time, then `create_step()` is called again (idempotency), 
the `start` time is preserved instead of being NULL'd out.

## Support

For issues or questions, check:
1. Terminal logs for `[DB]` prefixed messages
2. SQLite database: `chainlit.db`
3. This documentation

---

**Version:** 1.0 (Two-Phase Model)  
**Last Updated:** 2025-12-26

