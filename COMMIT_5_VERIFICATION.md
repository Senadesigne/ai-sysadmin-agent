# Commit 5 Verification Guide

## Overview
This document describes how to verify the deterministic planning feature introduced in Commit 5.

**Branch:** `commit-5-starter-kit`

## What Changed

### New Files
- `app/core/orchestrator.py` - Deterministic plan generator and execution gate
- `tests/test_orchestrator.py` - Test suite for orchestrator
- `COMMIT_5_VERIFICATION.md` - This document

### Modified Files
- `app/ui/chat.py` - Integrated plan generation before LLM/RAG processing

### Configuration
- `EXECUTION_ENABLED` flag in `app/config/settings.py` (default: `false`)
- `ENABLE_EVENTS` flag controls event emission (already existed)

## Feature Behavior

### With EXECUTION_ENABLED=false (default)
1. User sends a message
2. App generates and displays JSON plan
3. App emits `plan_created` event (if `ENABLE_EVENTS=true`)
4. App displays message: "Execution is disabled..."
5. **Processing stops** - no LLM calls, no tools, no actions

### With EXECUTION_ENABLED=true
1. User sends a message
2. App generates and displays JSON plan
3. App emits `plan_created` event
4. App calls `execute_plan()` (currently no-op in v1.x)
5. App displays execution status message
6. (Optional) App continues with LLM/RAG flow if implemented

## Verification Steps

### 1. Run Unit Tests

```bash
# Run all tests
pytest tests/test_orchestrator.py -v

# Expected output: All tests pass
# - test_create_plan_returns_dict ✓
# - test_create_plan_max_10_steps ✓
# - test_create_plan_risky_keyword_restart ✓
# - test_execute_plan_disabled_by_default ✓
# - ... (20+ tests)
```

### 2. Start Chainlit Application

```bash
# Ensure you're in the project root
cd c:\Users\Senad\.gemini\antigravity\scratch\ai-sysadmin-agent

# Run the application
chainlit run main.py -w
```

### 3. Manual Testing - Safe Query

**Test Case:** Safe query should NOT require approval

1. Open browser to `http://localhost:8000`
2. Login with credentials: `admin` / `admin`
3. Send message: **"show server status"**

**Expected Behavior:**
- ✅ JSON plan is displayed first
- ✅ Plan has multiple steps (≤10)
- ✅ All steps have `"requires_approval": false`
- ✅ Message appears: "Execution is disabled. The plan above shows what would be done..."
- ✅ No further processing occurs

### 4. Manual Testing - Risky Action

**Test Case:** Risky keyword should trigger approval requirement

1. Send message: **"restart nginx on server1"**

**Expected Behavior:**
- ✅ JSON plan is displayed first
- ✅ Plan contains keyword "restart"
- ✅ At least ONE step has `"requires_approval": true`
- ✅ `safety_notes` mention "potentially destructive actions"
- ✅ Message appears: "Execution is disabled..."
- ✅ No further processing occurs

### 5. Manual Testing - Empty Input

**Test Case:** Empty or whitespace input should not crash

1. Send message: **"   "** (whitespace only)

**Expected Behavior:**
- ✅ Fallback plan is displayed
- ✅ Plan has exactly 1 step: "Request clarification from user"
- ✅ App does not crash
- ✅ Message appears: "Execution is disabled..."

### 6. Verify Event Logging

**Test Case:** `plan_created` events are logged

1. Send message: **"check disk space on all servers"**
2. Check events log:

```bash
# View events log
cat .data/events.jsonl | tail -n 5
```

**Expected Output:**
```json
{"ts":"2025-12-28T...", "event_type":"plan_created", "data":{"goal":"check disk space on all servers", "number_of_steps":5, "requires_approval_count":0}}
```

**Verify:**
- ✅ Event contains `goal` (truncated to 100 chars)
- ✅ Event contains `number_of_steps`
- ✅ Event contains `requires_approval_count`
- ✅ Event does NOT contain raw user input beyond goal
- ✅ Event does NOT contain secrets or sensitive data

### 7. Determinism Test

**Test Case:** Same input produces same plan

1. Send message: **"restart apache"**
2. Note the plan steps (IDs, actions)
3. Refresh browser and start new chat
4. Send same message: **"restart apache"**
5. Compare plans

**Expected Behavior:**
- ✅ Both plans have identical structure
- ✅ Step IDs match
- ✅ Step actions match
- ✅ `requires_approval` flags match
- ✅ No random variations

### 8. Test with EXECUTION_ENABLED=true (Optional)

**Setup:**
```bash
# Add to .env file
echo "EXECUTION_ENABLED=true" >> .env

# Restart Chainlit
chainlit run main.py -w
```

**Test:**
1. Send message: **"list devices"**

**Expected Behavior:**
- ✅ Plan is displayed
- ✅ Execution status message: "Execution pipeline not implemented in v1.x..."
- ✅ App does NOT perform actual destructive actions (still no-op)
- ✅ App may continue to LLM/RAG flow (if implemented)

## Risky Keywords Reference

The following keywords trigger `requires_approval=true`:
- `restart`, `reboot`, `shutdown`, `halt`, `stop`
- `delete`, `remove`, `rm`, `kill`, `drop`
- `install`, `upgrade`, `update`, `modify`
- `write`, `format`, `destroy`

## Error Handling Tests

### Test 1: Plan generation never crashes
```python
# Run this in Python shell
from app.core.orchestrator import create_plan

# These should all return valid plans without raising
create_plan("")
create_plan(None)  # Will be handled
create_plan("a" * 10000)  # Very long input
create_plan("special chars: !@#$%^&*()")
```

### Test 2: Execution never crashes
```python
from app.core.orchestrator import execute_plan

# These should all return valid results without raising
execute_plan({})
execute_plan({"invalid": "structure"})
execute_plan(None)  # Will be handled
```

## Success Criteria

✅ All unit tests pass (`pytest tests/test_orchestrator.py`)  
✅ Plans are displayed BEFORE any LLM/tool calls  
✅ Plans are deterministic (same input → same plan)  
✅ Max 10 steps enforced  
✅ Risky keywords trigger approval flags  
✅ Safe queries do not require approval  
✅ Empty input returns fallback plan  
✅ `plan_created` events are logged to `.data/events.jsonl`  
✅ With `EXECUTION_ENABLED=false`: processing stops after plan  
✅ With `EXECUTION_ENABLED=true`: execution message shown (no-op)  
✅ No crashes on any input (error handling works)  

## Troubleshooting

### Events not appearing in log
- Check: `ENABLE_EVENTS=true` in `.env` or environment
- Check: `.data/events.jsonl` file exists and is writable
- Check: Console for `[EVENTS] WARNING` messages

### Plans not displaying
- Check: `app/ui/chat.py` imports orchestrator correctly
- Check: Console for `[ORCHESTRATOR] ERROR` messages
- Check: No exceptions in Chainlit logs

### Tests failing
- Ensure you're in project root: `cd c:\Users\Senad\.gemini\antigravity\scratch\ai-sysadmin-agent`
- Ensure pytest is installed: `pip install pytest`
- Run with verbose: `pytest tests/test_orchestrator.py -v`

## Next Steps

After verifying Commit 5:

1. ✅ Merge to main branch
2. Consider implementing actual execution logic (currently no-op)
3. Consider LLM-based plan generation (currently heuristic)
4. Add plan approval UI buttons (like existing action approval)
5. Add plan history/audit viewing

## Commit Message

```
feat: deterministic planning before execution

- Add app/core/orchestrator.py with deterministic plan generator
- Integrate plan display in chat.py (shown before LLM/RAG)
- Add execution gate controlled by EXECUTION_ENABLED flag
- Emit plan_created events to events.jsonl
- Add comprehensive test suite (tests/test_orchestrator.py)
- Plans are deterministic, max 10 steps, risky actions flagged
- Default: execution disabled (planner-only mode)
```

## Documentation

- Architecture: See `ARCHITECTURE.md` for system design
- Code Style: See `CODE_STYLE.md` for conventions
- Events: See `app/core/events.py` for event logging details
- Config: See `app/config/settings.py` for all flags

