# Commit 7 Verification — Event Emissions (Minimal)

**Branch:** `commit-7-starter-kit`  
**Objective:** Wire key event emissions at critical points (guarded by `ENABLE_EVENTS`).

---

## What Was Implemented

### 1. Event Emissions Added
The following events are now emitted at key points in the application flow:

#### LLM Events
- **`llm_call_start`** — Emitted before LLM invoke
  - Payload: `provider`, `model`, `prompt_len`, `has_images`, `thread_id`
  - Location: `app/ui/chat.py` (before `llm.invoke()`)

- **`llm_call_end`** — Emitted after LLM invoke (success or failure)
  - Success payload: `success: true`, `duration_ms`
  - Failure payload: `success: false`, `error_type`
  - Location: `app/ui/chat.py` (after `llm.invoke()` or in exception handler)

- **`llm_fallback`** — Already exists from Commit 3
  - Emitted when LLM falls back to NullLLM (offline mode, missing API key, init error)
  - Location: `app/llm/client.py`

#### RAG Events
- **`rag_query`** — Already exists from Commit 4
  - Emitted when RAG query is executed
  - Location: `app/rag/engine.py`

- **`rag_fallback`** — Already exists from Commit 4
  - Emitted when RAG is disabled or query fails
  - Location: `app/rag/engine.py`

#### Approval & Execution Events
- **`approval_requested`** — Emitted when action requires user approval
  - Payload: `action: "execution"`, `hostname_trunc`, `command_len`, `thread_id`
  - **NO raw command** is logged (only command length for privacy)
  - Location: `app/ui/chat.py` (when `cl.Action` buttons are created)

- **`execution_requested`** — Emitted when user approves execution
  - Payload: `hostname_trunc`, `command_len`, `thread_id`
  - **NO raw command** is logged
  - Location: `app/ui/chat.py` (`on_approve` callback)

#### Other Events
- **`plan_created`** — Already exists from Commit 6
  - Emitted when orchestrator creates a plan
  - Location: `app/ui/chat.py`

- **`chat_started`** — Already exists from Commit 2
  - Emitted when a new chat session starts
  - Location: `app/ui/chat.py`

---

## Security & Privacy

All event emissions follow strict sanitization rules:
- ✅ **NO raw user input** is logged
- ✅ **NO full commands** are logged (only command length)
- ✅ **NO API keys, passwords, or secrets**
- ✅ **NO file paths** (e.g., SSH key paths)
- ✅ **Hostnames are truncated** to max 30 characters
- ✅ **Text fields are truncated** to max 100 characters where applicable
- ✅ **All emissions are wrapped in try/except** (fail-safe, never crash the app)

---

## Manual Verification Tests

### Test 1: LLM Call Events

**Steps:**
1. Set `ENABLE_EVENTS=true` in `.env`
2. Start the app: `python main.py`
3. Login and send a chat message (e.g., "What devices are in inventory?")
4. Check `.data/events.jsonl`

**Expected Events:**
```
llm_call_start — with provider, model, prompt_len, has_images, thread_id
llm_call_end   — with success: true, duration_ms
```

**PowerShell Command:**
```powershell
Select-String -Path .\.data\events.jsonl -Pattern "llm_call_start|llm_call_end"
```

**Expected Output:**
```
{"ts":"2025-01-15T12:34:56.789Z","event_type":"llm_call_start","data":{"provider":"google","model":"gemini-3-pro-preview","prompt_len":523,"has_images":false,"thread_id":"abc123"}}
{"ts":"2025-01-15T12:34:58.123Z","event_type":"llm_call_end","data":{"success":true,"duration_ms":1334}}
```

---

### Test 2: Approval & Execution Events

**Steps:**
1. Ensure `ENABLE_EVENTS=true` and `EXECUTION_ENABLED=true`
2. Start the app and login
3. Send a message that triggers an action (e.g., "Check disk usage on server01")
4. Wait for LLM to generate action with approve/reject buttons
5. Click **✅ ODOBRI** (approve)
6. Check `.data/events.jsonl`

**Expected Events:**
```
approval_requested   — when action buttons are shown
execution_requested  — when user clicks approve
```

**PowerShell Command:**
```powershell
Select-String -Path .\.data\events.jsonl -Pattern "approval_requested|execution_requested"
```

**Expected Output:**
```
{"ts":"2025-01-15T12:35:10.456Z","event_type":"approval_requested","data":{"action":"execution","hostname_trunc":"server01","command_len":28,"thread_id":"abc123"}}
{"ts":"2025-01-15T12:35:15.789Z","event_type":"execution_requested","data":{"hostname_trunc":"server01","command_len":28,"thread_id":"abc123"}}
```

**Verify:**
- ✅ Command length is logged (e.g., `command_len: 28`)
- ✅ **NO full command text** appears in the log

---

### Test 3: RAG & Fallback Events

**Steps:**
1. Set `ENABLE_EVENTS=true` and `RAG_ENABLED=true`
2. Start the app and login
3. Send a message that would trigger RAG query (e.g., "Tell me about VLANs")
4. Check `.data/events.jsonl`

**Expected Events:**
```
rag_query — when RAG search is performed
```

**PowerShell Command:**
```powershell
Select-String -Path .\.data\events.jsonl -Pattern "rag_query|rag_fallback"
```

**Expected Output:**
```
{"ts":"2025-01-15T12:36:20.123Z","event_type":"rag_query","data":{"operation":"query","k":3}}
```

If RAG is disabled or fails:
```
{"ts":"2025-01-15T12:36:20.123Z","event_type":"rag_fallback","data":{"reason":"offline_mode","component":"NullRagEngine"}}
```

---

### Test 4: Complete Flow (All Events)

**Steps:**
1. Set `ENABLE_EVENTS=true`, `EXECUTION_ENABLED=true`, `OFFLINE_MODE=false`
2. Configure `GOOGLE_API_KEY` (valid key)
3. Start app, login, send a message that triggers action
4. Approve the action
5. Check all events

**PowerShell Command (filter all key events):**
```powershell
Select-String -Path .\.data\events.jsonl -Pattern "chat_started|plan_created|llm_call_start|llm_call_end|rag_query|rag_fallback|approval_requested|execution_requested|llm_fallback"
```

**Expected Flow:**
```
chat_started        → user logs in
plan_created        → orchestrator generates plan
rag_query           → RAG search executed
llm_call_start      → LLM invoked
llm_call_end        → LLM response received
approval_requested  → action requires approval
execution_requested → user approves action
```

---

## Automated Tests

Run the event tests:
```bash
pytest tests/test_events.py -v
```

**Test Coverage:**
- ✅ `test_llm_call_events` — Verify llm_call_start and llm_call_end structure
- ✅ `test_llm_call_error_event` — Verify llm_call_end on failure
- ✅ `test_approval_requested_event` — Verify approval_requested payload (sanitized)
- ✅ `test_execution_requested_event` — Verify execution_requested payload (sanitized)
- ✅ `test_event_emission_does_not_log_secrets` — Verify NO sensitive data is logged

---

## Event Log Location

Events are written to: `.data/events.jsonl`

Each line is a JSON object:
```json
{
  "ts": "2025-01-15T12:34:56.789Z",
  "event_type": "llm_call_start",
  "data": { ... }
}
```

---

## Troubleshooting

### Events Not Appearing?
1. Check `ENABLE_EVENTS=true` in `.env`
2. Verify `.data/` directory exists (auto-created)
3. Check console for `[EVENTS] WARNING:` messages

### Old Events in Log?
Events are **append-only**. To start fresh:
```bash
rm .data/events.jsonl
```

---

## Summary

✅ **Commit 7 COMPLETE**
- LLM call start/end events wired
- Approval/execution events wired
- RAG events already implemented (Commit 4)
- All events sanitized (no raw input, secrets, or commands)
- All emissions are fail-safe (never crash the app)
- Tests added for new events
- Events guarded by `ENABLE_EVENTS` flag

**Next:** Commit 8 (if planned) — or release preparation.

