"""
Tests for event logging infrastructure.
"""
import json
import os
from pathlib import Path

import pytest

from app.core.events import EventEmitter, JSONLEventLogger, get_emitter


def test_emit_creates_jsonl_line(tmp_path, monkeypatch):
    """
    Test that emit() creates a JSONL line with proper structure.
    """
    # Setup: use tmp_path for events file
    events_file = tmp_path / "events.jsonl"
    monkeypatch.setenv("EVENTS_PATH", str(events_file))
    
    # Force singleton reset (in case other tests initialized it)
    import app.core.events
    app.core.events._emitter = None
    
    # Emit an event
    emitter = get_emitter()
    emitter.emit("chat_started", {"auth_mode": "dev", "thread_id": "x"})
    
    # Verify file exists
    assert events_file.exists()
    
    # Read last line
    with open(events_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    assert len(lines) == 1
    
    # Parse JSON
    event = json.loads(lines[0])
    
    # Verify structure
    assert event["event_type"] == "chat_started"
    assert "ts" in event
    assert event["ts"].endswith("+00:00") or event["ts"].endswith("Z")  # UTC timestamp
    assert "data" in event
    assert event["data"]["auth_mode"] == "dev"
    assert event["data"]["thread_id"] == "x"


def test_emit_does_not_crash_on_write_error(tmp_path, monkeypatch):
    """
    Test that emit() does not crash if write fails.
    Logging errors must never crash the app.
    """
    events_file = tmp_path / "events.jsonl"
    monkeypatch.setenv("EVENTS_PATH", str(events_file))
    
    # Force singleton reset
    import app.core.events
    app.core.events._emitter = None
    
    # Get emitter
    emitter = get_emitter()
    
    # Monkeypatch write_event to raise exception
    original_write = JSONLEventLogger.write_event
    
    def failing_write(self, event):
        raise IOError("Simulated write failure")
    
    monkeypatch.setattr(JSONLEventLogger, "write_event", failing_write)
    
    # This should NOT raise - must be caught internally
    try:
        emitter.emit("test_event", {"test": "data"})
        # Success - no exception raised
    except Exception as e:
        pytest.fail(f"emit() should not crash on write error, but got: {e}")


def test_multiple_events_append(tmp_path, monkeypatch):
    """
    Test that multiple events are appended (not overwritten).
    """
    events_file = tmp_path / "events.jsonl"
    monkeypatch.setenv("EVENTS_PATH", str(events_file))
    
    # Force singleton reset
    import app.core.events
    app.core.events._emitter = None
    
    emitter = get_emitter()
    
    # Emit multiple events
    emitter.emit("event_1", {"count": 1})
    emitter.emit("event_2", {"count": 2})
    emitter.emit("event_3", {"count": 3})
    
    # Read all lines
    with open(events_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    assert len(lines) == 3
    
    # Verify each event
    events = [json.loads(line) for line in lines]
    assert events[0]["event_type"] == "event_1"
    assert events[0]["data"]["count"] == 1
    assert events[1]["event_type"] == "event_2"
    assert events[1]["data"]["count"] == 2
    assert events[2]["event_type"] == "event_3"
    assert events[2]["data"]["count"] == 3

