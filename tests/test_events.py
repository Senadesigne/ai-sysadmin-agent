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


def test_llm_call_events(tmp_path, monkeypatch):
    """
    Test that llm_call_start and llm_call_end events are emitted correctly.
    """
    events_file = tmp_path / "events.jsonl"
    monkeypatch.setenv("EVENTS_PATH", str(events_file))
    
    # Force singleton reset
    import app.core.events
    app.core.events._emitter = None
    
    emitter = get_emitter()
    
    # Emit llm_call_start
    emitter.emit("llm_call_start", {
        "provider": "google",
        "model": "gemini-3-pro-preview",
        "prompt_len": 1234,
        "has_images": False,
        "thread_id": "test-thread-123"
    })
    
    # Emit llm_call_end (success)
    emitter.emit("llm_call_end", {
        "success": True,
        "duration_ms": 567
    })
    
    # Read events
    with open(events_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    assert len(lines) == 2
    
    # Verify llm_call_start
    start_event = json.loads(lines[0])
    assert start_event["event_type"] == "llm_call_start"
    assert start_event["data"]["provider"] == "google"
    assert start_event["data"]["model"] == "gemini-3-pro-preview"
    assert start_event["data"]["prompt_len"] == 1234
    assert start_event["data"]["has_images"] is False
    assert start_event["data"]["thread_id"] == "test-thread-123"
    
    # Verify llm_call_end
    end_event = json.loads(lines[1])
    assert end_event["event_type"] == "llm_call_end"
    assert end_event["data"]["success"] is True
    assert end_event["data"]["duration_ms"] == 567


def test_llm_call_error_event(tmp_path, monkeypatch):
    """
    Test that llm_call_end emits error information on failure.
    """
    events_file = tmp_path / "events.jsonl"
    monkeypatch.setenv("EVENTS_PATH", str(events_file))
    
    # Force singleton reset
    import app.core.events
    app.core.events._emitter = None
    
    emitter = get_emitter()
    
    # Emit llm_call_end (failure)
    emitter.emit("llm_call_end", {
        "success": False,
        "error_type": "APIError"
    })
    
    # Read events
    with open(events_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    assert len(lines) == 1
    
    # Verify error event
    error_event = json.loads(lines[0])
    assert error_event["event_type"] == "llm_call_end"
    assert error_event["data"]["success"] is False
    assert error_event["data"]["error_type"] == "APIError"


def test_approval_requested_event(tmp_path, monkeypatch):
    """
    Test that approval_requested event is emitted with sanitized data.
    """
    events_file = tmp_path / "events.jsonl"
    monkeypatch.setenv("EVENTS_PATH", str(events_file))
    
    # Force singleton reset
    import app.core.events
    app.core.events._emitter = None
    
    emitter = get_emitter()
    
    # Emit approval_requested (no raw command, only length)
    emitter.emit("approval_requested", {
        "action": "execution",
        "hostname_trunc": "server01.example.com",
        "command_len": 45,
        "thread_id": "test-thread-456"
    })
    
    # Read events
    with open(events_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    assert len(lines) == 1
    
    # Verify approval event
    approval_event = json.loads(lines[0])
    assert approval_event["event_type"] == "approval_requested"
    assert approval_event["data"]["action"] == "execution"
    assert approval_event["data"]["hostname_trunc"] == "server01.example.com"
    assert approval_event["data"]["command_len"] == 45
    assert approval_event["data"]["thread_id"] == "test-thread-456"
    
    # Verify NO raw command is logged
    event_str = json.dumps(approval_event)
    assert "rm -rf" not in event_str  # Example: dangerous command should never appear


def test_execution_requested_event(tmp_path, monkeypatch):
    """
    Test that execution_requested event is emitted with sanitized data.
    """
    events_file = tmp_path / "events.jsonl"
    monkeypatch.setenv("EVENTS_PATH", str(events_file))
    
    # Force singleton reset
    import app.core.events
    app.core.events._emitter = None
    
    emitter = get_emitter()
    
    # Emit execution_requested (no raw command, only length)
    emitter.emit("execution_requested", {
        "hostname_trunc": "server02.example.com",
        "command_len": 32,
        "thread_id": "test-thread-789"
    })
    
    # Read events
    with open(events_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    assert len(lines) == 1
    
    # Verify execution event
    exec_event = json.loads(lines[0])
    assert exec_event["event_type"] == "execution_requested"
    assert exec_event["data"]["hostname_trunc"] == "server02.example.com"
    assert exec_event["data"]["command_len"] == 32
    assert exec_event["data"]["thread_id"] == "test-thread-789"
    
    # Verify NO raw command is logged
    event_str = json.dumps(exec_event)
    assert "systemctl" not in event_str  # Example: real command should never appear


def test_event_emission_does_not_log_secrets(tmp_path, monkeypatch):
    """
    Test that events never contain sensitive data (API keys, passwords, etc).
    This is a meta-test ensuring sanitization strategy.
    """
    events_file = tmp_path / "events.jsonl"
    monkeypatch.setenv("EVENTS_PATH", str(events_file))
    
    # Force singleton reset
    import app.core.events
    app.core.events._emitter = None
    
    emitter = get_emitter()
    
    # Emit various events with safe data
    emitter.emit("test_event", {
        "prompt_len": 100,  # OK - just length
        "has_images": True,  # OK - boolean
        "hostname_trunc": "srv"[:30],  # OK - truncated
        "command_len": 50  # OK - just length
    })
    
    # Read events
    with open(events_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Verify NO sensitive keywords appear
    forbidden_keywords = [
        "GOOGLE_API_KEY",
        "password",
        "secret",
        "api_key",
        "private_key",
        "SSH_KEY_PATH"
    ]
    
    for keyword in forbidden_keywords:
        assert keyword not in content, f"Event log contains sensitive keyword: {keyword}"