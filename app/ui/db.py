import aiosqlite
import asyncio
from app.config import settings

DB_PATH = settings.CHAINLIT_DB_PATH

_db_initialized = False
_db_init_lock = asyncio.Lock()

async def init_db():
    """Initialize SQLite database with required tables for Chainlit persistence."""
    settings.ensure_data_dirs()
    print(f"[starter-kit] Using Chainlit DB at: {DB_PATH}")

    async with aiosqlite.connect(str(DB_PATH)) as db:
        # Omogući Foreign Keys
        await db.execute("PRAGMA foreign_keys = ON;")

        # Kreiranje tablice users
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                identifier TEXT UNIQUE NOT NULL,
                metadata TEXT,
                createdAt TEXT NOT NULL
            )
        """)
        
        # Kreiranje tablice threads
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
        
        # Kreiranje tablice steps
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
        
        # Kreiranje tablice elements
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
        
        # Kreiranje tablice feedbacks
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
        _ = cursor.rowcount  # keep migration behavior; noise cleanup is a later step
        
        await db.commit()

async def ensure_db_init() -> None:
    global _db_initialized
    if _db_initialized:
        return
    async with _db_init_lock:
        if _db_initialized:
            return
        await init_db()
        _db_initialized = True