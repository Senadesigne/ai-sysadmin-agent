# Commit 2: Event Hooks Verification

## What was implemented

1. **New module: `app/core/events.py`**
   - `JSONLEventLogger` - Writes append-only events to `.data/events.jsonl` (UTF-8, one JSON per line)
   - `EventEmitter` - Adds timezone-aware UTC timestamps via `datetime.now(timezone.utc).isoformat()`
   - Safe error handling - never crashes app if write fails (try/except + print warning)
   - `get_emitter()` singleton with ENV override support (`EVENTS_PATH` or default `.data/events.jsonl`)

2. **Minimal wiring in `app/ui/chat.py`**
   - `on_chat_start` now emits `"chat_started"` event
   - Logs minimal data:
     - `auth_mode` (from environment)
     - `thread_id` (if available from session)
     - `user_identifier` (if available from user context)
   - **Does NOT log secrets** (no password/api_key/tokens)

3. **No external integrations added**
4. **No tests added** (per instructions - foundation only)

## Manual Verification (2 steps)

### Step 1: Start the app
```bash
python main.py
# or
chainlit run app/ui/chat.py
```

### Step 2: Open a new chat
1. Open your browser to the app URL (typically http://localhost:8000)
2. Log in (if auth is enabled)
3. Start a new chat session

### Step 3: Verify the event file
Check that `.data/events.jsonl` was created with a new line:

**Windows:**
```powershell
Get-Content .data\events.jsonl | Select-Object -Last 1
```

**Linux/Mac:**
```bash
tail -1 .data/events.jsonl
```

**Expected output format:**
```json
{"ts": "2025-12-27T08:54:45.123456+00:00", "event_type": "chat_started", "auth_mode": "dev", "user_identifier": "admin", "thread_id": "..."}
```

**Verification checklist:**
- ✅ File `.data/events.jsonl` exists
- ✅ New line added on each chat start
- ✅ Contains `ts` field with ISO 8601 UTC timestamp
- ✅ Contains `event_type: "chat_started"`
- ✅ Contains available context fields (auth_mode, user_identifier, thread_id)
- ✅ No passwords or secrets logged
- ✅ App does not crash if event logging fails

## Architecture Notes

- **Append-only design:** Events are never modified or deleted
- **Fail-safe:** Logging errors are caught and logged to console, never crash the app
- **Timezone-aware:** All timestamps use UTC with timezone info
- **ENV override:** Set `EVENTS_PATH=/custom/path/events.jsonl` to change location
- **Foundation for future:** This is the base for audit logs, analytics, webhooks, etc.

## Next Steps (Future Commits)

- Add more event types (command_executed, file_uploaded, etc.)
- Add event replay/analysis tools
- Add external integrations (webhooks, Slack, etc.)
- Add comprehensive tests
- Add documentation

