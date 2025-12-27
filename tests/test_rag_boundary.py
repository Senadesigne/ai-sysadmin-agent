"""
Test suite for Commit 4: RAG boundary - no-crash guarantees.

Tests verify:
1. OFFLINE_MODE returns NullRagEngine with empty results
2. Query errors are caught and return [] without crashing
3. Ingest errors are caught and return 0 without crashing
4. Events are emitted properly when ENABLE_EVENTS=true
5. No events emitted when ENABLE_EVENTS=false
6. No secrets/sensitive data in events or logs
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from app.rag.engine import get_rag_engine, NullRagEngine, RagEngine, _emit_rag_event


class TestOfflineMode:
    """Test OFFLINE_MODE returns NullRagEngine."""
    
    def test_offline_mode_returns_null_engine(self):
        """When OFFLINE_MODE=true, get_rag_engine should return NullRagEngine."""
        with patch.dict(os.environ, {"OFFLINE_MODE": "true"}):
            # Force reload of settings module to pick up env change
            import importlib
            from app.config import settings
            importlib.reload(settings)
            
            engine = get_rag_engine()
            assert isinstance(engine, NullRagEngine)
            assert engine.is_enabled is False
    
    def test_null_engine_query_returns_empty(self):
        """NullRagEngine.query() should return empty list."""
        engine = NullRagEngine(reason="offline")
        result = engine.query("test question")
        assert result == []
    
    def test_null_engine_ingest_document_returns_zero(self):
        """NullRagEngine.ingest_document() should return 0."""
        engine = NullRagEngine(reason="offline")
        result = engine.ingest_document("test.pdf")
        assert result == 0
    
    def test_null_engine_ingest_markdown_returns_zero(self):
        """NullRagEngine.ingest_markdown() should return 0."""
        engine = NullRagEngine(reason="offline")
        result = engine.ingest_markdown("test.md")
        assert result == 0


class TestRagQueryErrors:
    """Test query error handling - must not crash."""
    
    @patch('app.rag.engine.RagEngine.__init__', return_value=None)
    def test_query_error_returns_empty_list(self, mock_init):
        """When query() raises an exception, it should return [] instead of crashing."""
        engine = RagEngine()
        engine.is_enabled = True
        
        # Mock vector_store to raise an exception
        engine.vector_store = MagicMock()
        engine.vector_store.similarity_search.side_effect = RuntimeError("Simulated query error")
        
        # Should not crash, should return empty list
        result = engine.query("test question")
        assert result == []
    
    @patch('app.rag.engine.RagEngine.__init__', return_value=None)
    def test_query_disabled_engine_returns_empty(self, mock_init):
        """When engine is disabled, query should return []."""
        engine = RagEngine()
        engine.is_enabled = False
        engine.vector_store = None
        
        result = engine.query("test question")
        assert result == []


class TestRagIngestErrors:
    """Test ingest error handling - must not crash."""
    
    @patch('app.rag.engine.RagEngine.__init__', return_value=None)
    def test_ingest_document_error_returns_zero(self, mock_init):
        """When ingest_document() encounters error, it should return 0 instead of crashing."""
        engine = RagEngine()
        engine.is_enabled = True
        engine.vector_store = MagicMock()
        
        # Mock file exists but parsing fails
        with patch('os.path.exists', return_value=True):
            with patch('app.rag.engine.LlamaParse') as mock_parser:
                mock_parser.return_value.load_data.side_effect = RuntimeError("Parse error")
                
                # Should not crash, should return 0
                result = engine.ingest_document("test.pdf")
                assert result == 0
    
    @patch('app.rag.engine.RagEngine.__init__', return_value=None)
    def test_ingest_markdown_error_returns_zero(self, mock_init):
        """When ingest_markdown() encounters error, it should return 0 instead of crashing."""
        engine = RagEngine()
        engine.is_enabled = True
        engine.vector_store = MagicMock()
        
        # Mock file exists but reading fails
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', side_effect=IOError("Read error")):
                # Should not crash, should return 0
                result = engine.ingest_markdown("test.md")
                assert result == 0
    
    @patch('app.rag.engine.RagEngine.__init__', return_value=None)
    def test_ingest_disabled_engine_returns_zero(self, mock_init):
        """When engine is disabled, ingest should return 0."""
        engine = RagEngine()
        engine.is_enabled = False
        
        result = engine.ingest_document("test.pdf")
        assert result == 0
        
        result = engine.ingest_markdown("test.md")
        assert result == 0


class TestEventEmission:
    """Test event emission is fail-safe and respects ENABLE_EVENTS flag."""
    
    def test_events_disabled_no_emission(self):
        """When ENABLE_EVENTS=false, no events should be emitted."""
        with patch.dict(os.environ, {"ENABLE_EVENTS": "false"}):
            # Force reload of settings
            import importlib
            from app.config import settings
            importlib.reload(settings)
            
            with patch('app.core.events.get_emitter') as mock_get_emitter:
                _emit_rag_event("test_event", {"key": "value"})
                
                # get_emitter should NOT be called when ENABLE_EVENTS=false
                mock_get_emitter.assert_not_called()
    
    def test_events_enabled_emission(self):
        """When ENABLE_EVENTS=true, events should be emitted."""
        with patch.dict(os.environ, {"ENABLE_EVENTS": "true"}):
            # Force reload of settings
            import importlib
            from app.config import settings
            importlib.reload(settings)
            
            with patch('app.core.events.get_emitter') as mock_get_emitter:
                mock_emitter = MagicMock()
                mock_get_emitter.return_value = mock_emitter
                
                _emit_rag_event("rag_fallback", {"reason": "query_error", "error_type": "RuntimeError"})
                
                # Verify emit was called
                mock_emitter.emit.assert_called_once()
                call_args = mock_emitter.emit.call_args
                assert call_args[0][0] == "rag_fallback"
                assert call_args[0][1]["reason"] == "query_error"
                assert call_args[0][1]["error_type"] == "RuntimeError"
    
    def test_event_emission_never_crashes(self):
        """Event emission failures should never crash the app."""
        with patch.dict(os.environ, {"ENABLE_EVENTS": "true"}):
            # Force reload of settings
            import importlib
            from app.config import settings
            importlib.reload(settings)
            
            with patch('app.core.events.get_emitter', side_effect=Exception("Event system failure")):
                # This should not raise an exception
                try:
                    _emit_rag_event("test_event", {"key": "value"})
                    # If we get here, the test passes
                except Exception as e:
                    pytest.fail(f"Event emission crashed the app: {e}")
    
    def test_no_secrets_in_events(self):
        """Verify that events do not contain API keys or secrets."""
        with patch.dict(os.environ, {"ENABLE_EVENTS": "true"}):
            # Force reload of settings
            import importlib
            from app.config import settings
            importlib.reload(settings)
            
            with patch('app.core.events.get_emitter') as mock_get_emitter:
                mock_emitter = MagicMock()
                mock_get_emitter.return_value = mock_emitter
                
                # Emit a fallback event
                _emit_rag_event("rag_fallback", {
                    "reason": "init_error",
                    "error_type": "ValueError",
                    "component": "RagEngine"
                })
                
                # Verify emit was called
                mock_emitter.emit.assert_called_once()
                event_data = mock_emitter.emit.call_args[0][1]
                
                # Check that event data doesn't contain common secret keywords
                event_str = json.dumps(event_data).lower()
                assert "api_key" not in event_str
                assert "password" not in event_str
                assert "secret" not in event_str
                assert "token" not in event_str


class TestRagFallbackScenarios:
    """Test various RAG fallback scenarios emit appropriate events."""
    
    def test_offline_mode_emits_fallback_event(self):
        """NullRagEngine created for offline mode should emit rag_fallback."""
        with patch.dict(os.environ, {"ENABLE_EVENTS": "true"}):
            # Force reload of settings
            import importlib
            from app.config import settings
            importlib.reload(settings)
            
            with patch('app.core.events.get_emitter') as mock_get_emitter:
                mock_emitter = MagicMock()
                mock_get_emitter.return_value = mock_emitter
                
                # Create NullRagEngine with offline reason
                engine = NullRagEngine(reason="offline")
                
                # Should have emitted rag_fallback event
                mock_emitter.emit.assert_called()
                event_type = mock_emitter.emit.call_args[0][0]
                event_data = mock_emitter.emit.call_args[0][1]
                
                assert event_type == "rag_fallback"
                assert event_data["reason"] == "offline_mode"
    
    @patch('app.rag.engine.RagEngine.__init__', return_value=None)
    def test_query_error_emits_fallback_event(self, mock_init):
        """Query errors should emit rag_fallback event."""
        with patch.dict(os.environ, {"ENABLE_EVENTS": "true"}):
            # Force reload of settings
            import importlib
            from app.config import settings
            importlib.reload(settings)
            
            with patch('app.core.events.get_emitter') as mock_get_emitter:
                mock_emitter = MagicMock()
                mock_get_emitter.return_value = mock_emitter
                
                engine = RagEngine()
                engine.is_enabled = True
                engine.vector_store = MagicMock()
                engine.vector_store.similarity_search.side_effect = RuntimeError("Query failed")
                
                # Execute query (should fail gracefully)
                result = engine.query("test")
                
                # Should return empty list
                assert result == []
                
                # Should have emitted events (rag_query + rag_fallback)
                assert mock_emitter.emit.call_count >= 2
                
                # Check last call was rag_fallback
                last_call = mock_emitter.emit.call_args_list[-1]
                assert last_call[0][0] == "rag_fallback"
                assert last_call[0][1]["reason"] == "query_error"
                assert last_call[0][1]["error_type"] == "RuntimeError"


class TestIntegrationScenarios:
    """Integration tests for end-to-end RAG boundary behavior."""
    
    def test_rag_disabled_chat_still_works(self):
        """When RAG is disabled, chat should still work (return empty context)."""
        with patch.dict(os.environ, {"RAG_ENABLED": "false"}):
            # Force reload of settings
            import importlib
            from app.config import settings
            importlib.reload(settings)
            
            engine = get_rag_engine()
            assert isinstance(engine, NullRagEngine)
            
            # Query should return empty list
            context = engine.query("test question")
            assert context == []
            
            # This represents the chat still working with empty context
            # (The agent would just respond without knowledge base)
    
    def test_broken_rag_dependency_graceful_fallback(self):
        """When RAG dependencies fail to initialize, app should gracefully fallback."""
        with patch.dict(os.environ, {"RAG_ENABLED": "true", "OFFLINE_MODE": "false"}):
            # Force reload of settings
            import importlib
            from app.config import settings
            importlib.reload(settings)
            
            # Mock GoogleGenerativeAIEmbeddings to fail
            with patch('app.rag.engine.GoogleGenerativeAIEmbeddings', side_effect=Exception("API Error")):
                # This should not crash, should return disabled engine
                engine = RagEngine()
                
                assert engine.is_enabled is False
                
                # Query should return empty list
                result = engine.query("test")
                assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
