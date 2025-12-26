import json
import uuid
import asyncio
import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict, Any

from chainlit.data import BaseDataLayer
from chainlit.types import ThreadDict, ThreadFilter, PaginatedResponse
from chainlit.user import User, PersistedUser
from chainlit.element import ElementDict
from chainlit.step import StepDict

# IMPORT: Sada je ispravan jer smo popravili ime varijable u db.py
from app.ui.db import DB_NAME, ensure_db_init 

class SQLiteDataLayer(BaseDataLayer):
    """
    Custom Data Layer implementacija za Chainlit koristeći aiosqlite.
    Omogućuje lokalno spremanje povijesti razgovora.
    """
    
    def __init__(self):
        self.db_path = DB_NAME
        print(f"[starter-kit] SQLiteDataLayer initialized at: {self.db_path}")
        
    
    def _get(self, obj, key, default=None):
        """Helper method to get value from dict or object"""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    async def build_debug_url(self) -> str:
        return ""
    
    async def close(self):
        pass

    # --- USER METHODS ---
    async def get_user(self, identifier: str) -> Optional[PersistedUser]:
        await ensure_db_init()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, identifier, metadata, createdAt FROM users WHERE identifier = ?",
                (identifier,)
            )
            row = await cursor.fetchone()
            if row:
                metadata = json.loads(row[2]) if row[2] else {}
                return PersistedUser(
                    id=row[0],
                    identifier=row[1],
                    metadata=metadata,
                    createdAt=row[3]
                )
        return None

    async def create_user(self, user: User) -> Optional[PersistedUser]:
        await ensure_db_init()
        identifier = self._get(user, "identifier")
        existing = await self.get_user(identifier)
        if existing:
            return existing
            
        user_id = self._get(user, "id") or str(uuid.uuid4())
        metadata = self._get(user, "metadata") or {}
        created_at = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (id, identifier, metadata, createdAt) VALUES (?,?,?,?)",
                (user_id, identifier, json.dumps(metadata), created_at)
            )
            await db.commit()
            
        return PersistedUser(id=user_id, identifier=identifier, metadata=metadata, createdAt=created_at)

    # --- THREAD METHODS ---
    async def get_thread(self, thread_id: str) -> Optional[ThreadDict]:
        print(f"[RESUME] get_thread called with thread_id={thread_id}")
        await ensure_db_init()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Find thread by ID (no user filtering for admin access in dev mode)
            cursor = await db.execute("SELECT * FROM threads WHERE id = ?", (str(thread_id),))
            thread_row = await cursor.fetchone()
            
            if not thread_row:
                print(f"[RESUME] SQL query returned no row for thread_id={thread_id}")
                return None
            
            print(f"[RESUME] SQL query found row: id={thread_row[0]} name={thread_row[2]} userId={thread_row[3]} userIdentifier={thread_row[4]}")
            
            # Mapiranje rezultata - koristimo eksplicitne indekse za sigurnost
            thread_data = {
                "id": thread_row[0],
                "createdAt": thread_row[1], 
                "name": thread_row[2],
                "userId": thread_row[3],
                "userIdentifier": thread_row[4],
                "tags": json.loads(thread_row[5]) if thread_row[5] else [],
                "metadata": json.loads(thread_row[6]) if thread_row[6] else {},
                "steps": [],
                "elements": []
            }

            # Load all steps for thread, sort by createdAt ASC
            # Koristimo SELECT * da dobijemo sva polja iz baze
            cursor = await db.execute(
                "SELECT * FROM steps WHERE threadId = ? ORDER BY createdAt ASC", 
                (str(thread_id),)
            )
            steps_rows = await cursor.fetchall()
            
            print(f"[DB] Found {len(steps_rows)} steps for thread {thread_id}")
            
            for s in steps_rows:
                # Mapiranje prema strukturi baze (21 polje)
                step = {
                    "id": s[0],
                    "name": s[1], 
                    "type": s[2],
                    "threadId": s[3],
                    "parentId": s[4],
                    # Dodatna polja iz baze
                    "disableFeedback": bool(s[5]) if s[5] is not None else False,
                    "streaming": bool(s[6]) if s[6] is not None else False,
                    "waitForAnswer": bool(s[7]) if s[7] is not None else False,
                    "isError": bool(s[8]) if s[8] is not None else False,
                    "metadata": json.loads(s[9]) if s[9] else {},
                    "tags": json.loads(s[10]) if s[10] else [],
                    "input": s[11] or "",
                    "output": s[12] or "",
                    "createdAt": s[13],
                    "start": s[14],
                    "end": s[15],
                    "generation": s[16],
                    "showInput": s[17],
                    "language": s[18],
                    "indent": s[19],
                    "defaultOpen": bool(s[20]) if s[20] is not None else False
                }
                thread_data["steps"].append(step)
            
            print(f"[RESUME] returning dict with keys: {list(thread_data.keys())}")
            print(f"[RESUME] thread_data type: {type(thread_data)}")
            return thread_data

    async def list_threads(self, pagination, filters):
        print(f"[DB] ENTER list_threads pagination={pagination} filters={filters}")
        await ensure_db_init()
        async with aiosqlite.connect(self.db_path) as db:
            query = "SELECT id, createdAt, name, userId, userIdentifier, tags, metadata FROM threads"
            params = []
            conditions = []
            
            # In dev mode, admin can see all threads - no user filtering
            if filters.search:
                conditions.append("name LIKE ?")
                params.append(f"%{filters.search}%")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY createdAt DESC"
            
            if hasattr(pagination, 'first') and pagination.first:
                query += f" LIMIT {pagination.first}"
            
            cursor = await db.execute(query, tuple(params))
            rows = await cursor.fetchall()
            
            threads = []
            for row in rows:
                threads.append({
                    "id": row[0],
                    "createdAt": row[1],
                    "name": row[2],
                    "userId": row[3],
                    "userIdentifier": row[4],
                    "tags": json.loads(row[5]) if row[5] else [],
                    "metadata": json.loads(row[6]) if row[6] else {}
                })
            
            # Debug log prvih 10 thread ID-eva
            print(f"[DB] list_threads ids: {[t.get('id') for t in threads[:10]]}")
            print(f"[DB] EXIT list_threads -> returning {len(threads)} threads")
            
            # Vraćaj PaginatedResponse objekt, ne dict
            return PaginatedResponse(
                data=threads, 
                pageInfo={"hasNextPage": False, "startCursor": None, "endCursor": None}
            )

    async def update_thread(self, thread_id: str, name: Optional[str] = None, user_id: Optional[str] = None, metadata: Optional[Dict] = None, tags: Optional[List[str]] = None):
        print(f"[DB] ENTER update_thread threadId={thread_id}, name={name}, userId={user_id}")
        async with aiosqlite.connect(self.db_path) as db:
            if name: 
                await db.execute("UPDATE threads SET name = ? WHERE id = ?", (name, thread_id))
            if user_id: 
                await db.execute("UPDATE threads SET userId = ? WHERE id = ?", (user_id, thread_id))
            if metadata: 
                await db.execute("UPDATE threads SET metadata = ? WHERE id = ?", (json.dumps(metadata), thread_id))
            if tags: 
                await db.execute("UPDATE threads SET tags = ? WHERE id = ?", (json.dumps(tags), thread_id))
            await db.commit()

    async def create_thread(self, thread_dict: Any) -> str:
        """Create new thread - uses UPSERT to handle race conditions"""
        await ensure_db_init()
        thread_id = self._get(thread_dict, "id") or str(uuid.uuid4())  # Allow passing existing ID
        created_at = datetime.utcnow().isoformat()
        name = self._get(thread_dict, "name")
        user_id = self._get(thread_dict, "userId") or self._get(thread_dict, "user_id")
        incoming_user_identifier = self._get(thread_dict, "userIdentifier") or self._get(thread_dict, "user_identifier")
        tags = json.dumps(self._get(thread_dict, "tags", []))
        metadata = json.dumps(self._get(thread_dict, "metadata", {}))
        
        print(f"[DB] ENTER create_thread threadId={thread_id}, userId={user_id}, userIdentifier={incoming_user_identifier}, name={name}")
        
        # Resolve proper userIdentifier - never save "system"
        user_identifier = None
        
        # If incoming userIdentifier is None, empty, or "system", resolve from userId
        if not incoming_user_identifier or incoming_user_identifier == "system":
            if user_id:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(
                        "SELECT identifier FROM users WHERE id = ?", 
                        (user_id,)
                    )
                    user_row = await cursor.fetchone()
                    if user_row:
                        user_identifier = user_row[0]
                    else:
                        print(f"[DB] create_thread WARNING: userId={user_id} not found in users table")
            else:
                print(f"[DB] create_thread WARNING: no userId provided, cannot resolve userIdentifier")
        else:
            user_identifier = incoming_user_identifier
        
        print(f"[DB] create_thread resolved userIdentifier={user_identifier} from userId={user_id} (incoming={incoming_user_identifier})")
        
        async with aiosqlite.connect(self.db_path) as db:
            # Use UPSERT: INSERT or UPDATE if exists (overwrite placeholder with real data)
            await db.execute(
                """INSERT INTO threads (id, createdAt, name, userId, userIdentifier, tags, metadata) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     name = COALESCE(excluded.name, threads.name),
                     userId = COALESCE(excluded.userId, threads.userId),
                     userIdentifier = CASE 
                       WHEN excluded.userIdentifier IS NOT NULL AND excluded.userIdentifier != 'system' 
                       THEN excluded.userIdentifier 
                       ELSE threads.userIdentifier 
                     END,
                     tags = COALESCE(excluded.tags, threads.tags),
                     metadata = COALESCE(excluded.metadata, threads.metadata)""",
                (thread_id, created_at, name, user_id, user_identifier, tags, metadata)
            )
            await db.commit()
        
        print(f"[DB] EXIT create_thread threadId={thread_id}")
        return thread_id

    async def delete_thread(self, thread_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM steps WHERE threadId = ?", (thread_id,))
            await db.execute("DELETE FROM elements WHERE threadId = ?", (thread_id,))
            await db.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
            await db.commit()

    # --- STEP METHODS ---
    async def create_step(self, step_dict: StepDict):
        """Create step - deterministic: only works if thread exists"""
        await ensure_db_init()
        
        val_thread = step_dict.get("threadId")
        val_type = step_dict.get("type")
        val_name = step_dict.get("name")
        
        print(f"[DB] ENTER create_step threadId={val_thread}, type={val_type}, name={val_name}")
        
        async with aiosqlite.connect(self.db_path) as db:
            # Retry loop: wait for thread to be created (race condition handling)
            thread_exists = False
            for attempt in range(20):
                cursor = await db.execute("SELECT 1 FROM threads WHERE id = ?", (val_thread,))
                if await cursor.fetchone():
                    thread_exists = True
                    break
                await asyncio.sleep(0.05)
            
            if not thread_exists:
                # Thread still doesn't exist after retries - skip step creation
                print(f"[DB] WARNING: create_step called for missing thread {val_thread} - skipping after 20 retries")
                return

            # Mapiranje polja
            val_id = step_dict.get("id")
            val_parent = step_dict.get("parentId")
            val_input = str(step_dict.get("input") or "")
            val_output = str(step_dict.get("output") or "")
            val_created = step_dict.get("createdAt") or datetime.utcnow().isoformat()
            val_meta = json.dumps(step_dict.get("metadata") or {})

            await db.execute(
                """INSERT OR REPLACE INTO steps (id, name, type, threadId, parentId, input, output, createdAt, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (val_id, val_name, val_type, val_thread, val_parent, val_input, val_output, val_created, val_meta)
            )
            await db.commit()
        
        print(f"[DB] EXIT create_step threadId={val_thread}")

    async def update_step(self, step_dict: StepDict):
        async with aiosqlite.connect(self.db_path) as db:
            if step_dict.get("output"):
                await db.execute("UPDATE steps SET output = ? WHERE id = ?", (str(step_dict["output"]), step_dict["id"]))
            if step_dict.get("input"):
                await db.execute("UPDATE steps SET input = ? WHERE id = ?", (str(step_dict["input"]), step_dict["id"]))
            await db.commit()

    async def delete_step(self, step_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM steps WHERE id = ?", (step_id,))
            await db.commit()

    # --- Ostale metode (prazne implementacije za sada) ---
    async def create_element(self, element_dict: ElementDict): pass
    async def get_element(self, thread_id: str, element_id: str): return None
    async def delete_element(self, element_id: str): pass
    async def upsert_feedback(self, feedback): return ""
    async def delete_feedback(self, feedback_id): pass
    async def get_thread_author(self, thread_id: str) -> str:
        """
        Vraća userIdentifier iz threads tablice za dati thread_id.
        Ako userIdentifier nije setovan, dohvaća users.identifier preko userId.
        Chainlit često poziva ovu funkciju prije get_thread za author check.
        In dev mode, return 'admin' to allow admin access to all threads.
        """
        await ensure_db_init()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT userId, userIdentifier FROM threads WHERE id = ?", 
                (str(thread_id),)
            )
            row = await cursor.fetchone()
            
            if not row:
                print(f"[RESUME] get_thread_author thread_id={thread_id} -> system")
                return "system"
            
            user_id, user_identifier = row[0], row[1]
            
            # Ako userId postoji i nije prazan -> return userId
            if user_id and user_id.strip():
                print(f"[RESUME] get_thread_author thread_id={thread_id} -> {user_id}")
                return user_id
            # else ako userIdentifier postoji -> return userIdentifier
            elif user_identifier:
                print(f"[RESUME] get_thread_author thread_id={thread_id} -> {user_identifier}")
                return user_identifier
            # else return "system"
            else:
                print(f"[RESUME] get_thread_author thread_id={thread_id} -> system")
                return "system"
    async def delete_user_session(self, id): pass