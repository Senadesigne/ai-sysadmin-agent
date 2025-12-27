"""
Tests for LLM boundary - no-crash guarantees.

Commit 3: No-crash LLM boundary (offline + safe fallback)

Tests verify that:
1. OFFLINE_MODE=true → get_llm() returns NullLLM, no crash
2. Provider init error → fallback to NullLLM, no crash
3. NullLLM implements compatible interface (invoke/ainvoke)
4. Events are emitted when fallback occurs (if ENABLE_EVENTS=true)

All tests are stable and do not call external APIs.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import json

from app.llm.client import get_llm, NullLLM, is_llm_configured
from langchain_core.messages import HumanMessage


class TestLLMBoundary:
    """Test suite for LLM boundary safety."""
    
    def teardown_method(self):
        """Clean up singleton emitter between tests."""
        import app.core.events as events_module
        events_module._emitter = None
    
    def test_offline_mode_returns_nullllm(self):
        """
        Test: OFFLINE_MODE=true → get_llm() returns NullLLM and does not crash.
        """
        # Arrange: mock OFFLINE_MODE and ensure we have a valid API key (to prove offline takes precedence)
        with patch.dict(os.environ, {
            "GOOGLE_API_KEY": "test_key_abc123",
            "OFFLINE_MODE": "true",
            "ENABLE_EVENTS": "false"  # Disable events for isolation
        }):
            # Mock settings module that is imported inside get_llm()
            with patch("app.config.settings.OFFLINE_MODE", True):
                with patch("app.config.settings.ENABLE_EVENTS", False):
                    # Act
                    llm = get_llm()
                    
                    # Assert
                    assert isinstance(llm, NullLLM), "Expected NullLLM when OFFLINE_MODE=true"
                    assert llm.is_configured is False
                    
                    # Verify NullLLM can be invoked without crash
                    response = llm.invoke([HumanMessage(content="test")])
                    assert hasattr(response, "content")
                    assert "offline" in response.content.lower()
    
    def test_missing_api_key_returns_nullllm(self):
        """
        Test: Missing/invalid API key → get_llm() returns NullLLM and does not crash.
        """
        # Arrange: remove API key
        with patch.dict(os.environ, {
            "GOOGLE_API_KEY": "",
            "OFFLINE_MODE": "false",
            "ENABLE_EVENTS": "false"
        }):
            with patch("app.config.settings.OFFLINE_MODE", False):
                with patch("app.config.settings.ENABLE_EVENTS", False):
                    # Act
                    llm = get_llm()
                    
                    # Assert
                    assert isinstance(llm, NullLLM), "Expected NullLLM when API key is missing"
                    assert llm.is_configured is False
                    
                    # Verify NullLLM can be invoked
                    response = llm.invoke([HumanMessage(content="test")])
                    assert hasattr(response, "content")
                    assert "unavailable" in response.content.lower()
    
    def test_provider_init_error_returns_nullllm(self):
        """
        Test: Provider initialization error → fallback to NullLLM, no crash.
        """
        # Arrange: mock ChatGoogleGenerativeAI to raise error
        with patch.dict(os.environ, {
            "GOOGLE_API_KEY": "test_key_valid",
            "OFFLINE_MODE": "false",
            "ENABLE_EVENTS": "false"
        }):
            with patch("app.config.settings.OFFLINE_MODE", False):
                with patch("app.config.settings.ENABLE_EVENTS", False):
                    with patch("app.llm.client.ChatGoogleGenerativeAI") as mock_llm_class:
                        # Simulate provider init error
                        mock_llm_class.side_effect = RuntimeError("API authentication failed")
                        
                        # Act
                        llm = get_llm()
                        
                        # Assert
                        assert isinstance(llm, NullLLM), "Expected NullLLM when provider init fails"
                        assert llm.is_configured is False
                        
                        # Verify NullLLM works
                        response = llm.invoke([HumanMessage(content="test")])
                        assert hasattr(response, "content")
    
    def test_nullllm_interface_compatibility(self):
        """
        Test: NullLLM implements compatible interface (invoke, ainvoke).
        """
        # Arrange
        null_llm = NullLLM(reason="test")
        
        # Act & Assert: invoke
        response = null_llm.invoke([HumanMessage(content="test")])
        assert hasattr(response, "content")
        assert isinstance(response.content, str)
        
        # Act & Assert: ainvoke (async)
        import asyncio
        response_async = asyncio.run(null_llm.ainvoke([HumanMessage(content="test")]))
        assert hasattr(response_async, "content")
        assert isinstance(response_async.content, str)
    
    def test_event_emission_on_fallback_offline(self):
        """
        Test: llm_fallback event is emitted when OFFLINE_MODE triggers fallback.
        """
        # Arrange: temporary events file
        with tempfile.TemporaryDirectory() as tmpdir:
            events_path = Path(tmpdir) / "events.jsonl"
            
            with patch.dict(os.environ, {
                "GOOGLE_API_KEY": "test_key",
                "OFFLINE_MODE": "true",
                "ENABLE_EVENTS": "true",
                "EVENTS_PATH": str(events_path),
                "AUTH_MODE": "dev"
            }):
                with patch("app.config.settings.OFFLINE_MODE", True):
                    with patch("app.config.settings.ENABLE_EVENTS", True):
                        # Act
                        llm = get_llm()
                        
                        # Assert: NullLLM returned
                        assert isinstance(llm, NullLLM)
                        
                        # Assert: event file created and contains llm_fallback event
                        assert events_path.exists(), "Events file should be created"
                        
                        with open(events_path, "r") as f:
                            events = [json.loads(line) for line in f]
                        
                        # Find llm_fallback event
                        fallback_events = [e for e in events if e.get("event_type") == "llm_fallback"]
                        assert len(fallback_events) > 0, "Expected at least one llm_fallback event"
                        
                        event = fallback_events[0]
                        assert event["data"]["reason"] == "offline_mode"
                        assert event["data"]["provider"] == "google"
                        assert "auth_mode" in event["data"]  # Optional field
    
    def test_event_emission_on_fallback_missing_key(self):
        """
        Test: llm_fallback event is emitted when API key is missing.
        """
        # Arrange: temporary events file
        with tempfile.TemporaryDirectory() as tmpdir:
            events_path = Path(tmpdir) / "events.jsonl"
            
            with patch.dict(os.environ, {
                "GOOGLE_API_KEY": "",
                "OFFLINE_MODE": "false",
                "ENABLE_EVENTS": "true",
                "EVENTS_PATH": str(events_path)
            }):
                with patch("app.config.settings.OFFLINE_MODE", False):
                    with patch("app.config.settings.ENABLE_EVENTS", True):
                        # Act
                        llm = get_llm()
                        
                        # Assert
                        assert isinstance(llm, NullLLM)
                        assert events_path.exists()
                        
                        with open(events_path, "r") as f:
                            events = [json.loads(line) for line in f]
                        
                        fallback_events = [e for e in events if e.get("event_type") == "llm_fallback"]
                        assert len(fallback_events) > 0
                        assert fallback_events[0]["data"]["reason"] == "missing_api_key"
    
    def test_event_emission_on_fallback_init_error(self):
        """
        Test: llm_fallback event is emitted when provider init fails.
        """
        # Arrange: temporary events file
        with tempfile.TemporaryDirectory() as tmpdir:
            events_path = Path(tmpdir) / "events.jsonl"
            
            with patch.dict(os.environ, {
                "GOOGLE_API_KEY": "test_key",
                "OFFLINE_MODE": "false",
                "ENABLE_EVENTS": "true",
                "EVENTS_PATH": str(events_path)
            }):
                with patch("app.config.settings.OFFLINE_MODE", False):
                    with patch("app.config.settings.ENABLE_EVENTS", True):
                        with patch("app.llm.client.ChatGoogleGenerativeAI") as mock_llm_class:
                            mock_llm_class.side_effect = ValueError("Invalid credentials")
                            
                            # Act
                            llm = get_llm()
                            
                            # Assert
                            assert isinstance(llm, NullLLM)
                            assert events_path.exists()
                            
                            with open(events_path, "r") as f:
                                events = [json.loads(line) for line in f]
                            
                            fallback_events = [e for e in events if e.get("event_type") == "llm_fallback"]
                            assert len(fallback_events) > 0
                            assert fallback_events[0]["data"]["reason"] == "provider_init_error"
                            assert "error_type" in fallback_events[0]["data"]
    
    def test_no_events_when_disabled(self):
        """
        Test: No events are emitted when ENABLE_EVENTS=false (fail-safe).
        """
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            events_path = Path(tmpdir) / "events.jsonl"
            
            with patch.dict(os.environ, {
                "GOOGLE_API_KEY": "",
                "OFFLINE_MODE": "false",
                "ENABLE_EVENTS": "false",
                "EVENTS_PATH": str(events_path)
            }):
                with patch("app.config.settings.OFFLINE_MODE", False):
                    with patch("app.config.settings.ENABLE_EVENTS", False):
                        # Act
                        llm = get_llm()
                        
                        # Assert: NullLLM returned but no events file created
                        assert isinstance(llm, NullLLM)
                        assert not events_path.exists(), "Events file should not be created when ENABLE_EVENTS=false"
    
    def test_is_llm_configured_helper(self):
        """
        Test: is_llm_configured() helper function works correctly.
        """
        # Test with valid key
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "valid_key"}):
            assert is_llm_configured() is True
        
        # Test with missing key
        with patch.dict(os.environ, {"GOOGLE_API_KEY": ""}):
            assert is_llm_configured() is False
        
        # Test with placeholder key
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "ovdje_ide_key"}):
            assert is_llm_configured() is False
        
        # Test with whitespace-only key
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "   "}):
            assert is_llm_configured() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

