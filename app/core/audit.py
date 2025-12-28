"""
Audit trail module for tracking approvals and critical actions.

This module provides append-only audit logging to .data/audit.jsonl.
All audit operations are wrapped in try/except to ensure they never crash the app.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.config.settings import DATA_DIR, ENABLE_AUDIT


# Audit log path
AUDIT_LOG_PATH = DATA_DIR / "audit.jsonl"


def log_audit(
    user: Optional[str],
    action: str,
    params: Optional[Dict[str, Any]] = None,
    outcome: Optional[str] = None
) -> bool:
    """
    Log an audit entry to the audit trail.
    
    Args:
        user: User identifier (e.g., username or email). None if user context unavailable.
        action: Action type (e.g., "approve", "reject", "execute").
        params: Optional dictionary of action parameters (hostname, command, etc.).
        outcome: Optional outcome description (e.g., "success", "error", "cancelled").
    
    Returns:
        bool: True if audit entry was written successfully, False otherwise.
    
    Note:
        This function never raises exceptions. All errors are silently handled
        to prevent audit logging from crashing the application.
    """
    # Skip if audit is disabled
    if not ENABLE_AUDIT:
        return False
    
    try:
        # Ensure .data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Build audit entry
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": user,
            "action": action,
            "params": params or {},
            "outcome": outcome
        }
        
        # Append to audit log (JSONL format - one JSON object per line)
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        return True
        
    except Exception as e:
        # Silent failure - audit must never crash the app
        # In production, this could be logged to a separate error log
        # For now, we just return False
        return False


def read_audit_log(limit: Optional[int] = None) -> list[Dict[str, Any]]:
    """
    Read audit log entries.
    
    Args:
        limit: Maximum number of entries to return (most recent first). None for all.
    
    Returns:
        list: List of audit entries as dictionaries.
    
    Note:
        This function is primarily for testing and inspection.
        In production, audit logs should be accessed via secure channels only.
    """
    entries = []
    
    try:
        if not AUDIT_LOG_PATH.exists():
            return entries
        
        with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        entries.append(entry)
                    except json.JSONDecodeError:
                        # Skip malformed lines
                        continue
        
        # Return most recent first
        entries.reverse()
        
        if limit is not None:
            entries = entries[:limit]
        
        return entries
        
    except Exception:
        # Silent failure - return empty list
        return []

