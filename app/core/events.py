"""
Event logging infrastructure.

Provides append-only JSONL event logging for audit and analytics.
Events are written to .data/events.jsonl by default.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class JSONLEventLogger:
    """
    Append-only JSON Lines event logger.
    Each event is written as a single JSON object per line.
    """
    
    def __init__(self, path: str | Path):
        """
        Initialize logger with target file path.
        
        Args:
            path: Path to the .jsonl file
        """
        self.path = Path(path).resolve()
        # Ensure parent directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)
    
    def write_event(self, event: Dict[str, Any]) -> None:
        """
        Write a single event to the JSONL file.
        
        Args:
            event: Event dictionary to log
        """
        try:
            with open(self.path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        except Exception as e:
            # Never crash the app due to logging failure
            print(f"[EVENT WARNING] Failed to write event to {self.path}: {e}")


class EventEmitter:
    """
    Event emitter that adds timestamps and delegates to logger.
    """
    
    def __init__(self, logger: JSONLEventLogger):
        """
        Initialize emitter with a logger.
        
        Args:
            logger: JSONLEventLogger instance
        """
        self.logger = logger
    
    def emit(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit an event with automatic timestamp.
        
        Args:
            event_type: Type of event (e.g., "chat_started")
            data: Optional event data dictionary
        """
        if data is None:
            data = {}
        
        # Add timezone-aware UTC timestamp
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            **data
        }
        
        self.logger.write_event(event)


# Singleton instance
_emitter: Optional[EventEmitter] = None


def get_emitter() -> EventEmitter:
    """
    Get or create the singleton EventEmitter instance.
    
    Uses EVENTS_PATH environment variable if set, otherwise defaults to .data/events.jsonl
    
    Returns:
        EventEmitter singleton instance
    """
    global _emitter
    
    if _emitter is None:
        # Get path from environment or use default
        events_path = os.getenv("EVENTS_PATH")
        if events_path is None:
            # Default to .data/events.jsonl relative to repo root
            from app.config.settings import DATA_DIR
            events_path = DATA_DIR / "events.jsonl"
        
        logger = JSONLEventLogger(events_path)
        _emitter = EventEmitter(logger)
    
    return _emitter

