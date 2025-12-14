import json
import uuid
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
        # print(f" SQLiteDataLayer inicijaliziran na: {self.db_path}")
    
    def _get(self, obj, key, default=None):
        """Helper metoda za dohvaćanje vrijednosti iz dict ili objekta"""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    async def build_debug_url(self) -> str:
        return ""
    
    async def close(self):
        pass

    # --- USER METHODS ---
    async def get_user(self, identifier: str) -> Optional[PersistedUser]:
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
        await ensure_db_init()
        async with aiosqlite.connect(self.db_path) as db:
            # Thread
            cursor = await db.execute("SELECT id, createdAt, name, userId, userIdentifier, tags, metadata FROM threads WHERE id = ?", (thread_id,))
            row = await cursor.fetchone()
            if not row: 
                return None
            
            # Mapiranje rezultata
            thread_data = {
                "id": row[0],
                "createdAt": row[1],
                "name": row[2],
                "userId": row[3],
                "userIdentifier": row[4],
                "tags": json.loads(row[5]) if row[5] else [],
                "metadata": json.loads(row[6]) if row[6] else {},
                "steps": [],
                "elements": []
            }

            # Steps
            cursor = await db.execute("SELECT id, name, type, threadId, parentId, input, output, createdAt, metadata FROM steps WHERE threadId = ? ORDER BY createdAt ASC", (thread_id,))
            steps_rows = await cursor.fetchall()
            for s in steps_rows:
                step = {
                    "id": s[0],
                    "name": s[1],
                    "type": s[2],
                    "threadId": s[3],
                    "parentId": s[4],
                    "input": s[5],
                    "output": s[6],
                    "createdAt": s[7],
                    "metadata": json.loads(s[8]) if s[8] else {}
                }
                thread_data["steps"].append(step)
            
            return thread_data

    async def list_threads(self, pagination: Any, filters: ThreadFilter) -> PaginatedResponse:
        await ensure_db_init()
        async with aiosqlite.connect(self.db_path) as db:
            query = "SELECT id, createdAt, name, userId, userIdentifier, tags, metadata FROM threads"
            params = []
            conditions = []
            
            # Temporarily disable user filter to show all threads
            # if filters.userId:
            #     conditions.append("(userId = ? OR userIdentifier = ?)")
            #     params.extend([filters.userId, filters.userId])
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
            
            print(f"[DB] list_threads (NO user filter) -> {len(threads)} threads")
            return PaginatedResponse(data=threads, pageInfo={"hasNextPage": False, "startCursor": None, "endCursor": None})

    async def update_thread(self, thread_id: str, name: Optional[str] = None, user_id: Optional[str] = None, metadata: Optional[Dict] = None, tags: Optional[List[str]] = None):
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
        """Kreira novi thread"""
        await ensure_db_init()
        thread_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        name = self._get(thread_dict, "name")
        user_id = self._get(thread_dict, "userId") or self._get(thread_dict, "user_id")
        user_identifier = self._get(thread_dict, "userIdentifier") or self._get(thread_dict, "user_identifier")
        tags = json.dumps(self._get(thread_dict, "tags", []))
        metadata = json.dumps(self._get(thread_dict, "metadata", {}))
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO threads (id, createdAt, name, userId, userIdentifier, tags, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (thread_id, created_at, name, user_id, user_identifier, tags, metadata)
            )
            await db.commit()
        
        return thread_id

    async def delete_thread(self, thread_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM steps WHERE threadId = ?", (thread_id,))
            await db.execute("DELETE FROM elements WHERE threadId = ?", (thread_id,))
            await db.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
            await db.commit()

    # --- STEP METHODS ---
    async def create_step(self, step_dict: StepDict):
        await ensure_db_init()
        async with aiosqlite.connect(self.db_path) as db:
            # Self-healing: Ako thread ne postoji, kreiraj ga
            cursor = await db.execute("SELECT 1 FROM threads WHERE id = ?", (step_dict["threadId"],))
            if not await cursor.fetchone():
                await db.execute(
                    "INSERT INTO threads (id, createdAt, name, userIdentifier) VALUES (?, ?, ?, ?)", 
                    (step_dict["threadId"], datetime.utcnow().isoformat(), "Auto-created", "system")
                )

            # Mapiranje polja
            val_id = step_dict.get("id")
            val_name = step_dict.get("name")
            val_type = step_dict.get("type")
            val_thread = step_dict.get("threadId")
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
    async def get_thread_author(self, thread_id): return ""
    async def delete_user_session(self, id): pass