import aiosqlite
import logging
import asyncio
from pathlib import Path

# DB path stabilizacija - apsolutni path u root projekta
# db.py je u app/ui/, pa trebamo ići 2 razine gore do root-a
ROOT_DIR = Path(__file__).resolve().parents[2]
DB_NAME = str(ROOT_DIR / "chainlit.db")

# Debug print - prikaži gdje je DB
print(f"[DB] DB path: {DB_NAME}")

# Jednokratna inicijalizacija
_db_initialized = False
_db_init_lock = asyncio.Lock()

async def init_db():
    """Initialize SQLite database with required tables for Chainlit persistence."""
    print(f"[starter-kit] Using Chainlit DB at: {DB_NAME}")
    async with aiosqlite.connect(DB_NAME) as db:
        # Omogući Foreign Keys
        await db.execute("PRAGMA foreign_keys = ON;")

        # Create users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                identifier TEXT UNIQUE NOT NULL,
                metadata TEXT,
                createdAt TEXT NOT NULL
            )
        """)
        
        # Create threads table
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
        
        # Create steps table
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
        
        # Create elements table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS elements (
                id TEXT PRIMARY KEY,
                threadId TEXT NOT NULL,
                type TEXT NOT NULL,
                url TEXT,
                chainlitKey TEXT,
                name TEXT NOT NULL,
                display TEXT,
                objectKey TEXT,
                size TEXT,
                mime TEXT,
                path TEXT,
                language TEXT,
                forId TEXT,
                props TEXT,
                FOREIGN KEY (threadId) REFERENCES threads(id) ON DELETE CASCADE
            )
        """)
        
        # Create feedbacks table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id TEXT PRIMARY KEY,
                forId TEXT,
                threadId TEXT NOT NULL,
                value INTEGER NOT NULL,
                comment TEXT,
                FOREIGN KEY (threadId) REFERENCES threads(id) ON DELETE CASCADE
            )
        """)
        
        # One-time migration: Popuni userIdentifier za postojeće threadove
        cursor = await db.execute("""
            UPDATE threads 
            SET userIdentifier = (
                SELECT users.identifier 
                FROM users 
                WHERE users.id = threads.userId
            ) 
            WHERE (userIdentifier IS NULL OR userIdentifier = 'system') AND userId IS NOT NULL
        """)
        migrated_count = cursor.rowcount
        if migrated_count > 0:
            print(f"[DB] Migrated {migrated_count} threads with userIdentifier (including system -> proper identifier)")
        
        await db.commit()
        print("[DB] init_db complete (tables ensured: users, threads, steps, elements, feedbacks)")

async def ensure_db_init() -> bool:
    """
    Ensure DB is initialized.
    
    Returns:
        True if DB init succeeded (or was already initialized)
        False if DB init failed (never raises exceptions)
    """
    global _db_initialized
    if _db_initialized:
        return True
    
    async with _db_init_lock:
        if _db_initialized:
            return True
        
        try:
            await init_db()
            _db_initialized = True
            return True
        except Exception as e:
            print(f"[DB] ERROR: Failed to initialize database: {e}")
            return False