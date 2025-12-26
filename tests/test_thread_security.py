"""
Production-grade security tests for two-phase thread persistence.

Tests verify:
1. get_thread_author returns None for pending/missing threads
2. list_threads filters by userId and hides pending threads
3. get_thread blocks resume for pending threads
4. Two-phase flow creates pending then finalizes correctly
"""

import pytest
import pytest_asyncio
import sqlite3
import tempfile
import os
import asyncio
from datetime import datetime
from typing import Optional

# Import DataLayer
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ui.data_layer import SQLiteDataLayer
from app.ui.db import init_db
from chainlit.types import ThreadFilter, Pagination

# Mock Pagination class if not present
class MockPagination:
    def __init__(self, first=None):
        self.first = first

class MockFilter:
    def __init__(self, userId=None, search=None):
        self.userId = userId
        self.search = search

@pytest_asyncio.fixture
async def temp_db():
    """Create temporary SQLite database for testing"""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Override DB path in DataLayer
    original_db_name = SQLiteDataLayer.db_path if hasattr(SQLiteDataLayer, 'db_path') else None
    
    # Initialize test DB
    import aiosqlite
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        
        # Create schema
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                identifier TEXT UNIQUE NOT NULL,
                metadata TEXT,
                createdAt TEXT NOT NULL
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                createdAt TEXT NOT NULL,
                name TEXT,
                userId TEXT,
                userIdentifier TEXT,
                tags TEXT,
                metadata TEXT,
                FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS steps (
                id TEXT PRIMARY KEY,
                name TEXT,
                type TEXT NOT NULL,
                threadId TEXT NOT NULL,
                parentId TEXT,
                disableFeedback INTEGER DEFAULT 0,
                streaming INTEGER DEFAULT 0,
                waitForAnswer INTEGER DEFAULT 0,
                isError INTEGER DEFAULT 0,
                metadata TEXT,
                tags TEXT,
                input TEXT,
                output TEXT,
                createdAt TEXT NOT NULL,
                start TEXT,
                end TEXT,
                generation TEXT,
                showInput TEXT,
                language TEXT,
                indent INTEGER,
                defaultOpen INTEGER,
                FOREIGN KEY (threadId) REFERENCES threads(id) ON DELETE CASCADE
            )
        """)
        
        await db.commit()
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def data_layer(temp_db):
    """Create DataLayer instance with temp DB"""
    layer = SQLiteDataLayer()
    layer.db_path = temp_db
    return layer

@pytest.mark.asyncio
async def test_get_thread_author_missing_returns_none(data_layer):
    """BLOCKER TEST: get_thread_author returns None for non-existent threads"""
    result = await data_layer.get_thread_author("non-existent-thread-id")
    assert result is None, "get_thread_author should return None for missing thread"

@pytest.mark.asyncio
async def test_get_thread_author_pending_returns_none(data_layer):
    """BLOCKER TEST: get_thread_author returns None for pending threads"""
    import aiosqlite
    
    # Create pending thread (userId=NULL, userIdentifier=NULL)
    async with aiosqlite.connect(data_layer.db_path) as db:
        await db.execute(
            "INSERT INTO threads (id, createdAt, name, userId, userIdentifier, tags, metadata) VALUES (?, ?, NULL, NULL, NULL, '[]', '{}')",
            ("pending-thread-1", datetime.utcnow().isoformat())
        )
        await db.commit()
    
    # Test: get_thread_author should return None
    result = await data_layer.get_thread_author("pending-thread-1")
    assert result is None, "get_thread_author should return None for pending thread (no user context)"

@pytest.mark.asyncio
async def test_get_thread_author_completed_returns_identifier(data_layer):
    """BLOCKER TEST: get_thread_author returns userIdentifier for completed threads"""
    import aiosqlite
    
    # Create user
    async with aiosqlite.connect(data_layer.db_path) as db:
        await db.execute(
            "INSERT INTO users (id, identifier, metadata, createdAt) VALUES (?, ?, '{}', ?)",
            ("user-123", "alice", datetime.utcnow().isoformat())
        )
        
        # Create complete thread
        await db.execute(
            "INSERT INTO threads (id, createdAt, name, userId, userIdentifier, tags, metadata) VALUES (?, ?, ?, ?, ?, '[]', '{}')",
            ("thread-complete", datetime.utcnow().isoformat(), "Test Thread", "user-123", "alice")
        )
        await db.commit()
    
    # Test: get_thread_author should return userIdentifier
    result = await data_layer.get_thread_author("thread-complete")
    assert result == "alice", f"get_thread_author should return 'alice', got {result}"

@pytest.mark.asyncio
async def test_list_threads_filters_by_user(data_layer):
    """BLOCKER TEST: list_threads only returns threads for current user"""
    import aiosqlite
    
    # Create two users
    async with aiosqlite.connect(data_layer.db_path) as db:
        await db.execute("INSERT INTO users (id, identifier, metadata, createdAt) VALUES (?, ?, '{}', ?)",
                        ("user-alice", "alice", datetime.utcnow().isoformat()))
        await db.execute("INSERT INTO users (id, identifier, metadata, createdAt) VALUES (?, ?, '{}', ?)",
                        ("user-bob", "bob", datetime.utcnow().isoformat()))
        
        # Create threads for each user
        await db.execute(
            "INSERT INTO threads (id, createdAt, name, userId, userIdentifier, tags, metadata) VALUES (?, ?, ?, ?, ?, '[]', '{}')",
            ("thread-alice-1", datetime.utcnow().isoformat(), "Alice Thread 1", "user-alice", "alice")
        )
        await db.execute(
            "INSERT INTO threads (id, createdAt, name, userId, userIdentifier, tags, metadata) VALUES (?, ?, ?, ?, ?, '[]', '{}')",
            ("thread-alice-2", datetime.utcnow().isoformat(), "Alice Thread 2", "user-alice", "alice")
        )
        await db.execute(
            "INSERT INTO threads (id, createdAt, name, userId, userIdentifier, tags, metadata) VALUES (?, ?, ?, ?, ?, '[]', '{}')",
            ("thread-bob-1", datetime.utcnow().isoformat(), "Bob Thread 1", "user-bob", "bob")
        )
        await db.commit()
    
    # Test: list_threads as Alice
    filters_alice = MockFilter(userId="user-alice")
    pagination = MockPagination(first=10)
    result_alice = await data_layer.list_threads(pagination, filters_alice)
    
    alice_thread_ids = [t['id'] for t in result_alice.data]
    assert len(alice_thread_ids) == 2, f"Alice should see 2 threads, got {len(alice_thread_ids)}"
    assert "thread-alice-1" in alice_thread_ids, "Alice should see her own thread-alice-1"
    assert "thread-alice-2" in alice_thread_ids, "Alice should see her own thread-alice-2"
    assert "thread-bob-1" not in alice_thread_ids, "Alice should NOT see Bob's thread"
    
    # Test: list_threads as Bob
    filters_bob = MockFilter(userId="user-bob")
    result_bob = await data_layer.list_threads(pagination, filters_bob)
    
    bob_thread_ids = [t['id'] for t in result_bob.data]
    assert len(bob_thread_ids) == 1, f"Bob should see 1 thread, got {len(bob_thread_ids)}"
    assert "thread-bob-1" in bob_thread_ids, "Bob should see his own thread"
    assert "thread-alice-1" not in bob_thread_ids, "Bob should NOT see Alice's threads"

@pytest.mark.asyncio
async def test_list_threads_hides_pending(data_layer):
    """BLOCKER TEST: list_threads never returns pending threads"""
    import aiosqlite
    
    # Create user
    async with aiosqlite.connect(data_layer.db_path) as db:
        await db.execute("INSERT INTO users (id, identifier, metadata, createdAt) VALUES (?, ?, '{}', ?)",
                        ("user-charlie", "charlie", datetime.utcnow().isoformat()))
        
        # Create complete thread
        await db.execute(
            "INSERT INTO threads (id, createdAt, name, userId, userIdentifier, tags, metadata) VALUES (?, ?, ?, ?, ?, '[]', '{}')",
            ("thread-complete", datetime.utcnow().isoformat(), "Complete Thread", "user-charlie", "charlie")
        )
        
        # Create pending thread (no user context)
        await db.execute(
            "INSERT INTO threads (id, createdAt, name, userId, userIdentifier, tags, metadata) VALUES (?, ?, NULL, NULL, NULL, '[]', '{}')",
            ("thread-pending", datetime.utcnow().isoformat())
        )
        await db.commit()
    
    # Test: list_threads should only return complete thread
    filters = MockFilter(userId="user-charlie")
    pagination = MockPagination(first=10)
    result = await data_layer.list_threads(pagination, filters)
    
    thread_ids = [t['id'] for t in result.data]
    assert len(thread_ids) == 1, f"Should return 1 thread, got {len(thread_ids)}"
    assert "thread-complete" in thread_ids, "Should return complete thread"
    assert "thread-pending" not in thread_ids, "Should NOT return pending thread (security)"

@pytest.mark.asyncio
async def test_get_thread_blocks_pending(data_layer):
    """BLOCKER TEST: get_thread returns None for pending threads (blocks resume)"""
    import aiosqlite
    
    # Create pending thread
    async with aiosqlite.connect(data_layer.db_path) as db:
        await db.execute(
            "INSERT INTO threads (id, createdAt, name, userId, userIdentifier, tags, metadata) VALUES (?, ?, NULL, NULL, NULL, '[]', '{}')",
            ("thread-pending-resume", datetime.utcnow().isoformat())
        )
        await db.commit()
    
    # Test: get_thread should return None (blocks resume)
    result = await data_layer.get_thread("thread-pending-resume")
    assert result is None, "get_thread should return None for pending thread (blocks resume)"

@pytest.mark.asyncio
async def test_two_phase_flow_persists_steps_and_finalizes(data_layer):
    """BLOCKER TEST: Two-phase flow correctly creates pending thread then finalizes"""
    import aiosqlite
    
    thread_id = "test-two-phase-thread"
    
    # Create user first
    async with aiosqlite.connect(data_layer.db_path) as db:
        await db.execute("INSERT INTO users (id, identifier, metadata, createdAt) VALUES (?, ?, '{}', ?)",
                        ("user-test", "testuser", datetime.utcnow().isoformat()))
        await db.commit()
    
    # Phase A: create_step (creates pending thread)
    step_dict = {
        "id": "step-1",
        "threadId": thread_id,
        "type": "user_message",
        "name": "Test Step",
        "input": "test input",
        "output": "test output",
        "createdAt": datetime.utcnow().isoformat(),
        "metadata": {}
    }
    await data_layer.create_step(step_dict)
    
    # Verify: thread exists and is pending
    async with aiosqlite.connect(data_layer.db_path) as db:
        cursor = await db.execute("SELECT userId, userIdentifier FROM threads WHERE id = ?", (thread_id,))
        row = await cursor.fetchone()
        assert row is not None, "Thread should exist after create_step"
        assert row[0] is None and row[1] is None, "Thread should be pending (no user context)"
    
    # Verify: get_thread_author returns None for pending
    author = await data_layer.get_thread_author(thread_id)
    assert author is None, "get_thread_author should return None for pending thread"
    
    # Phase B: update_thread (finalizes thread with user data)
    await data_layer.update_thread(thread_id, name="Test Thread", user_id="user-test")
    
    # Verify: thread is now complete
    async with aiosqlite.connect(data_layer.db_path) as db:
        cursor = await db.execute("SELECT userId, userIdentifier, name FROM threads WHERE id = ?", (thread_id,))
        row = await cursor.fetchone()
        assert row[0] == "user-test", f"userId should be 'user-test', got {row[0]}"
        assert row[1] == "testuser", f"userIdentifier should be 'testuser', got {row[1]}"
        assert row[2] == "Test Thread", f"name should be 'Test Thread', got {row[2]}"
    
    # Verify: get_thread_author now returns userIdentifier
    author = await data_layer.get_thread_author(thread_id)
    assert author == "testuser", f"get_thread_author should return 'testuser', got {author}"
    
    # Verify: get_thread now returns thread data
    thread_data = await data_layer.get_thread(thread_id)
    assert thread_data is not None, "get_thread should return data for complete thread"
    assert thread_data['id'] == thread_id, "Thread ID should match"
    assert len(thread_data['steps']) == 1, "Thread should have 1 step"

@pytest.mark.asyncio
async def test_list_threads_fail_closed_without_user_filter(data_layer):
    """BLOCKER TEST: list_threads returns empty list when no userId filter (fail-closed)"""
    import aiosqlite
    
    # Create user and complete thread
    async with aiosqlite.connect(data_layer.db_path) as db:
        await db.execute("INSERT INTO users (id, identifier, metadata, createdAt) VALUES (?, ?, '{}', ?)",
                        ("user-failclosed", "failclosed", datetime.utcnow().isoformat()))
        await db.execute(
            "INSERT INTO threads (id, createdAt, name, userId, userIdentifier, tags, metadata) VALUES (?, ?, ?, ?, ?, '[]', '{}')",
            ("thread-failclosed", datetime.utcnow().isoformat(), "Test Thread", "user-failclosed", "failclosed")
        )
        await db.commit()
    
    # Test 1: No userId filter -> should return 0 threads (fail-closed)
    filters_empty = MockFilter(userId=None)
    pagination = MockPagination(first=10)
    result = await data_layer.list_threads(pagination, filters_empty)
    
    assert len(result.data) == 0, f"list_threads should return 0 threads without userId filter (fail-closed), got {len(result.data)}"
    
    # Test 2: Empty string userId -> should also return 0 threads
    filters_empty_string = MockFilter(userId="")
    result2 = await data_layer.list_threads(pagination, filters_empty_string)
    
    assert len(result2.data) == 0, f"list_threads should return 0 threads with empty userId filter, got {len(result2.data)}"

@pytest.mark.asyncio
async def test_list_threads_filters_by_userid_or_identifier(data_layer):
    """BLOCKER TEST: list_threads works with both userId (UUID) and userIdentifier (string)"""
    import aiosqlite
    import uuid
    
    # Create two users with UUIDs
    admin_uuid = str(uuid.uuid4())
    bob_uuid = str(uuid.uuid4())
    
    async with aiosqlite.connect(data_layer.db_path) as db:
        await db.execute("INSERT INTO users (id, identifier, metadata, createdAt) VALUES (?, ?, '{}', ?)",
                        (admin_uuid, "admin", datetime.utcnow().isoformat()))
        await db.execute("INSERT INTO users (id, identifier, metadata, createdAt) VALUES (?, ?, '{}', ?)",
                        (bob_uuid, "bob", datetime.utcnow().isoformat()))
        
        # Create threads: one for admin (with UUID + identifier), one for bob
        await db.execute(
            "INSERT INTO threads (id, createdAt, name, userId, userIdentifier, tags, metadata) VALUES (?, ?, ?, ?, ?, '[]', '{}')",
            ("thread-admin", datetime.utcnow().isoformat(), "Admin Thread", admin_uuid, "admin")
        )
        await db.execute(
            "INSERT INTO threads (id, createdAt, name, userId, userIdentifier, tags, metadata) VALUES (?, ?, ?, ?, ?, '[]', '{}')",
            ("thread-bob", datetime.utcnow().isoformat(), "Bob Thread", bob_uuid, "bob")
        )
        await db.commit()
    
    pagination = MockPagination(first=10)
    
    # Test 1: Filter by userIdentifier string "admin" -> should return admin thread
    filters_admin_identifier = MockFilter(userId="admin")
    result_admin_ident = await data_layer.list_threads(pagination, filters_admin_identifier)
    
    admin_threads_by_ident = [t['id'] for t in result_admin_ident.data]
    assert len(admin_threads_by_ident) == 1, f"Should return 1 thread for identifier 'admin', got {len(admin_threads_by_ident)}"
    assert "thread-admin" in admin_threads_by_ident, "Should return admin thread when filtering by identifier"
    assert "thread-bob" not in admin_threads_by_ident, "Should NOT return bob thread"
    
    # Test 2: Filter by userId UUID -> should also return admin thread (OR logic)
    filters_admin_uuid = MockFilter(userId=admin_uuid)
    result_admin_uuid = await data_layer.list_threads(pagination, filters_admin_uuid)
    
    admin_threads_by_uuid = [t['id'] for t in result_admin_uuid.data]
    assert len(admin_threads_by_uuid) == 1, f"Should return 1 thread for UUID {admin_uuid}, got {len(admin_threads_by_uuid)}"
    assert "thread-admin" in admin_threads_by_uuid, "Should return admin thread when filtering by UUID"
    
    # Test 3: Filter by bob identifier -> should return only bob thread
    filters_bob = MockFilter(userId="bob")
    result_bob = await data_layer.list_threads(pagination, filters_bob)
    
    bob_threads = [t['id'] for t in result_bob.data]
    assert len(bob_threads) == 1, f"Should return 1 thread for bob, got {len(bob_threads)}"
    assert "thread-bob" in bob_threads, "Should return bob thread"
    assert "thread-admin" not in bob_threads, "Should NOT return admin thread"

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])

