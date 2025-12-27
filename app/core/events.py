"""
Event logging infrastructure.

Provides append-only JSONL event logging for audit and analytics.
Events are written to DATA_DIR/events.jsonl by default (or EVENTS_PATH override).
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
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write_event(self, event: Dict[str, Any]) -> None:
        """
        Write a single event to the JSONL file.
        Never raises (logging must not crash the app).
        """
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[EVENTS] WARNING: Failed to write event to {self.path}: {e}")


class EventEmitter:
    """
    Event emitter that adds timestamps and delegates to logger.
    """

    def __init__(self, logger: JSONLEventLogger):
        self.logger = logger

    def emit(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit an event with automatic UTC timestamp.

        Event shape:
          {"ts": "...", "event_type": "...", "data": {...}}
        
        Never raises - logging must not crash the app.
        """
        if data is None:
            data = {}

        try:
            event = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "event_type": str(event_type),
                "data": data,
            }

            self.logger.write_event(event)
        except Exception as e:
            # Double safety: catch any exceptions that slip through
            print(f"[EVENTS] WARNING: Failed to emit event '{event_type}': {e}")


_emitter: Optional[EventEmitter] = None


def get_emitter() -> EventEmitter:
    """
    Get or create the singleton EventEmitter instance.

    Uses EVENTS_PATH env var if set, otherwise defaults to DATA_DIR/events.jsonl.
    """
    global _emitter

    if _emitter is None:
        events_path = os.getenv("EVENTS_PATH")
        if not events_path:
            from app.config.settings import DATA_DIR  # local import to avoid circular imports
            events_path = str(Path(DATA_DIR) / "events.jsonl")

        logger = JSONLEventLogger(events_path)
        _emitter = EventEmitter(logger)

    return _emitter
