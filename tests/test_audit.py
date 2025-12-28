"""
Tests for audit trail module (app/core/audit.py).

This test suite verifies that:
1. Audit entries are written correctly to .data/audit.jsonl
2. Audit logging never crashes the app (graceful failure)
3. Audit can be disabled via ENABLE_AUDIT flag
4. Audit entries contain expected fields with correct types
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.audit import log_audit, read_audit_log, AUDIT_LOG_PATH


@pytest.fixture
def temp_audit_log(tmp_path):
    """
    Create a temporary audit log for testing.
    Patches AUDIT_LOG_PATH to use temp directory.
    """
    temp_log_path = tmp_path / "audit.jsonl"
    
    with patch("app.core.audit.AUDIT_LOG_PATH", temp_log_path):
        with patch("app.core.audit.DATA_DIR", tmp_path):
            yield temp_log_path


def test_audit_log_basic_entry(temp_audit_log):
    """Test that a basic audit entry is written correctly."""
    # Enable audit for this test
    with patch("app.core.audit.ENABLE_AUDIT", True):
        result = log_audit(
            user="test_user",
            action="test_action",
            params={"key": "value"},
            outcome="success"
        )
        
        assert result is True
        assert temp_audit_log.exists()
        
        # Read and verify the entry
        with open(temp_audit_log, "r") as f:
            line = f.readline()
            entry = json.loads(line)
            
        assert entry["user"] == "test_user"
        assert entry["action"] == "test_action"
        assert entry["params"] == {"key": "value"}
        assert entry["outcome"] == "success"
        assert "timestamp" in entry


def test_audit_log_multiple_entries(temp_audit_log):
    """Test that multiple audit entries are appended correctly."""
    with patch("app.core.audit.ENABLE_AUDIT", True):
        # Write multiple entries
        log_audit("user1", "approve", {"host": "server1"}, "success")
        log_audit("user2", "reject", {"host": "server2"}, "cancelled")
        log_audit("user1", "approve", {"host": "server3"}, "error")
        
        # Read all entries
        with open(temp_audit_log, "r") as f:
            lines = f.readlines()
        
        assert len(lines) == 3
        
        # Verify each entry is valid JSON
        entries = [json.loads(line) for line in lines]
        
        assert entries[0]["user"] == "user1"
        assert entries[0]["action"] == "approve"
        assert entries[1]["user"] == "user2"
        assert entries[1]["action"] == "reject"
        assert entries[2]["outcome"] == "error"


def test_audit_log_disabled(temp_audit_log):
    """Test that audit logging is skipped when ENABLE_AUDIT is False."""
    with patch("app.core.audit.ENABLE_AUDIT", False):
        result = log_audit("user", "action", {}, "outcome")
        
        assert result is False
        assert not temp_audit_log.exists()


def test_audit_log_with_none_user(temp_audit_log):
    """Test that audit works when user is None (unauthenticated context)."""
    with patch("app.core.audit.ENABLE_AUDIT", True):
        result = log_audit(
            user=None,
            action="test_action",
            params={"key": "value"},
            outcome="success"
        )
        
        assert result is True
        
        with open(temp_audit_log, "r") as f:
            entry = json.loads(f.readline())
        
        assert entry["user"] is None
        assert entry["action"] == "test_action"


def test_audit_log_with_none_params_and_outcome(temp_audit_log):
    """Test that audit works with None params and outcome."""
    with patch("app.core.audit.ENABLE_AUDIT", True):
        result = log_audit(
            user="test_user",
            action="test_action",
            params=None,
            outcome=None
        )
        
        assert result is True
        
        with open(temp_audit_log, "r") as f:
            entry = json.loads(f.readline())
        
        assert entry["params"] == {}
        assert entry["outcome"] is None


def test_audit_log_with_complex_params(temp_audit_log):
    """Test that audit handles complex parameter dictionaries."""
    with patch("app.core.audit.ENABLE_AUDIT", True):
        complex_params = {
            "hostname": "server1.example.com",
            "command": "systemctl restart nginx",
            "reason": "User requested restart",
            "metadata": {
                "ip": "192.168.1.100",
                "os": "ubuntu"
            }
        }
        
        result = log_audit("user", "approve", complex_params, "success")
        
        assert result is True
        
        with open(temp_audit_log, "r") as f:
            entry = json.loads(f.readline())
        
        assert entry["params"] == complex_params
        assert entry["params"]["metadata"]["ip"] == "192.168.1.100"


def test_audit_log_graceful_failure():
    """Test that audit logging fails gracefully on write errors."""
    # Try to write to a read-only path (simulating write error)
    with patch("app.core.audit.ENABLE_AUDIT", True):
        with patch("app.core.audit.AUDIT_LOG_PATH", Path("/nonexistent/readonly/path/audit.jsonl")):
            # This should not raise an exception
            result = log_audit("user", "action", {}, "outcome")
            
            # Should return False on failure
            assert result is False


def test_read_audit_log(temp_audit_log):
    """Test reading audit log entries."""
    with patch("app.core.audit.ENABLE_AUDIT", True):
        # Write test entries
        log_audit("user1", "approve", {"host": "server1"}, "success")
        log_audit("user2", "reject", {"host": "server2"}, "cancelled")
        log_audit("user3", "approve", {"host": "server3"}, "success")
    
    # Read entries using the helper function
    with patch("app.core.audit.AUDIT_LOG_PATH", temp_audit_log):
        entries = read_audit_log()
    
    assert len(entries) == 3
    # Should be in reverse order (most recent first)
    assert entries[0]["user"] == "user3"
    assert entries[1]["user"] == "user2"
    assert entries[2]["user"] == "user1"


def test_read_audit_log_with_limit(temp_audit_log):
    """Test reading audit log with limit."""
    with patch("app.core.audit.ENABLE_AUDIT", True):
        # Write multiple entries
        for i in range(10):
            log_audit(f"user{i}", "action", {}, "success")
    
    # Read only the 3 most recent entries
    with patch("app.core.audit.AUDIT_LOG_PATH", temp_audit_log):
        entries = read_audit_log(limit=3)
    
    assert len(entries) == 3
    assert entries[0]["user"] == "user9"
    assert entries[1]["user"] == "user8"
    assert entries[2]["user"] == "user7"


def test_read_audit_log_empty(temp_audit_log):
    """Test reading audit log when it doesn't exist."""
    with patch("app.core.audit.AUDIT_LOG_PATH", temp_audit_log):
        entries = read_audit_log()
    
    assert entries == []


def test_read_audit_log_malformed_entries(temp_audit_log):
    """Test reading audit log with some malformed entries."""
    with patch("app.core.audit.ENABLE_AUDIT", True):
        # Write valid entry
        log_audit("user1", "approve", {}, "success")
    
    # Manually append malformed entry
    with open(temp_audit_log, "a") as f:
        f.write("{ invalid json }\n")
    
    # Write another valid entry
    with patch("app.core.audit.ENABLE_AUDIT", True):
        log_audit("user2", "reject", {}, "cancelled")
    
    # Read should skip malformed entry
    with patch("app.core.audit.AUDIT_LOG_PATH", temp_audit_log):
        entries = read_audit_log()
    
    # Should have 2 valid entries (malformed one skipped)
    assert len(entries) == 2
    assert entries[0]["user"] == "user2"
    assert entries[1]["user"] == "user1"


def test_audit_log_timestamp_format(temp_audit_log):
    """Test that timestamp is in ISO 8601 format with timezone."""
    with patch("app.core.audit.ENABLE_AUDIT", True):
        log_audit("user", "action", {}, "outcome")
        
        with open(temp_audit_log, "r") as f:
            entry = json.loads(f.readline())
        
        timestamp = entry["timestamp"]
        
        # Should be ISO 8601 format with timezone (ends with +00:00 or Z)
        assert "T" in timestamp
        assert any(marker in timestamp for marker in ["+", "Z"])


def test_audit_log_no_secrets_leak():
    """
    Test that audit logging doesn't accidentally log secrets.
    This is a contract test - params should be explicitly passed,
    never auto-captured from environment.
    """
    with patch("app.core.audit.ENABLE_AUDIT", True):
        # Set some environment secrets
        os.environ["SECRET_KEY"] = "super_secret_value"
        os.environ["API_KEY"] = "api_key_123"
        
        temp_log = Path(tempfile.gettempdir()) / "test_audit_secrets.jsonl"
        
        with patch("app.core.audit.AUDIT_LOG_PATH", temp_log):
            with patch("app.core.audit.DATA_DIR", Path(tempfile.gettempdir())):
                # Log an action
                log_audit(
                    user="user",
                    action="approve",
                    params={"hostname": "server1", "command": "ls"},
                    outcome="success"
                )
                
                # Read the log
                with open(temp_log, "r") as f:
                    content = f.read()
                
                # Verify secrets are NOT in the log
                assert "super_secret_value" not in content
                assert "api_key_123" not in content
                
                # Clean up
                temp_log.unlink()
        
        # Clean up env vars
        del os.environ["SECRET_KEY"]
        del os.environ["API_KEY"]


def test_audit_approval_scenario(temp_audit_log):
    """Integration test: simulate approval flow."""
    with patch("app.core.audit.ENABLE_AUDIT", True):
        # Simulate user approving an action
        log_audit(
            user="admin",
            action="approve",
            params={
                "hostname": "web-server-01",
                "command": "systemctl restart nginx"
            },
            outcome="success"
        )
        
        with open(temp_audit_log, "r") as f:
            entry = json.loads(f.readline())
        
        assert entry["user"] == "admin"
        assert entry["action"] == "approve"
        assert entry["outcome"] == "success"
        assert "hostname" in entry["params"]
        assert "command" in entry["params"]


def test_audit_rejection_scenario(temp_audit_log):
    """Integration test: simulate rejection flow."""
    with patch("app.core.audit.ENABLE_AUDIT", True):
        # Simulate user rejecting an action
        log_audit(
            user="admin",
            action="reject",
            params={
                "hostname": "db-server-01",
                "command": "rm -rf /data"
            },
            outcome="cancelled"
        )
        
        with open(temp_audit_log, "r") as f:
            entry = json.loads(f.readline())
        
        assert entry["user"] == "admin"
        assert entry["action"] == "reject"
        assert entry["outcome"] == "cancelled"


def test_audit_error_scenario(temp_audit_log):
    """Integration test: simulate error during execution."""
    with patch("app.core.audit.ENABLE_AUDIT", True):
        # Simulate approval that resulted in error
        log_audit(
            user="admin",
            action="approve",
            params={
                "hostname": "missing-server",
                "command": "uptime"
            },
            outcome="error_device_not_found"
        )
        
        with open(temp_audit_log, "r") as f:
            entry = json.loads(f.readline())
        
        assert entry["action"] == "approve"
        assert entry["outcome"] == "error_device_not_found"

