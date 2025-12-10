import os
import json
import chainlit.data as cl_data
from chainlit.types import ThreadDict, ThreadFilter, PaginatedResponse
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, String, Text, Integer, JSON, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import datetime
import uuid

# --- SQLALCHEMY SETUP ---
Base = declarative_base()

class DBUser(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    identifier = Column(String, unique=True, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)
    createdAt = Column(String, default=datetime.datetime.utcnow().isoformat)

class DBThread(Base):
    __tablename__ = "threads"
    id = Column(String, primary_key=True)
    createdAt = Column(String)
    name = Column(String, nullable=True)
    userId = Column(String, ForeignKey("users.id"), nullable=True)
    userIdentifier = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)

class DBStep(Base):
    __tablename__ = "steps"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    type = Column(String)
    threadId = Column(String, ForeignKey("threads.id"))
    parentId = Column(String, nullable=True)
    disableFeedback = Column(Integer, default=0) # Boolean as int
    streaming = Column(Integer, default=0)
    waitForAnswer = Column(Integer, default=0)
    isError = Column(Integer, default=0)
    metadata_ = Column("metadata", JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    input = Column(Text, nullable=True)
    output = Column(Text, nullable=True)
    createdAt = Column(String)
    start = Column(String, nullable=True)
    end = Column(String, nullable=True)
    generation = Column(JSON, nullable=True)
    showInput = Column(String, nullable=True)
    language = Column(String, nullable=True)
    indent = Column(Integer, nullable=True)


class DBElement(Base):
    __tablename__ = "elements"
    id = Column(String, primary_key=True)
    threadId = Column(String, ForeignKey("threads.id"))
    type = Column(String)
    url = Column(String, nullable=True)
    chainlitKey = Column(String, nullable=True)
    name = Column(String)
    display = Column(String)
    objectKey = Column(String, nullable=True)
    size = Column(String, nullable=True)
    mime = Column(String, nullable=True)
    path = Column(String, nullable=True)
    language = Column(String, nullable=True)
    forId = Column(String, nullable=True)

class DBFeedback(Base):
    __tablename__ = "feedbacks"
    id = Column(String, primary_key=True)
    forId = Column(String, nullable=True)
    value = Column(Integer) # 1 or -1
    comment = Column(Text, nullable=True)

class SQLiteDataLayer(cl_data.BaseDataLayer):
    def __init__(self, db_path="history.db"):
        self.db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(self.db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    # --- HELPER ---
    def _get(self, obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    # --- REQUIRED ABSTRACT METHODS ---
    async def build_debug_url(self) -> str:
        return ""

    async def get_thread_author(self, thread_id: str) -> str:
        with self.SessionLocal() as session:
            thread = session.query(DBThread).filter(DBThread.id == thread_id).first()
            if thread:
                return thread.userIdentifier
        return ""

    async def close(self):
        pass # Engine handles pool

    # --- ELEMENTS ---
    async def create_element(self, element_data: Any):
        with self.SessionLocal() as session:
            # Handle both dict (legacy) and object (chainlit 2.x)
            element = DBElement(
                id=self._get(element_data, "id"),
                threadId=self._get(element_data, "thread_id") or self._get(element_data, "threadId"),
                type=self._get(element_data, "type"),
                url=self._get(element_data, "url"),
                chainlitKey=self._get(element_data, "chainlit_key") or self._get(element_data, "chainlitKey"),
                name=self._get(element_data, "name"),
                display=self._get(element_data, "display"),
                objectKey=self._get(element_data, "object_key") or self._get(element_data, "objectKey"),
                size=str(self._get(element_data, "size")) if self._get(element_data, "size") else None,
                mime=self._get(element_data, "mime"),
                path=self._get(element_data, "path"),
                language=self._get(element_data, "language"),
                forId=self._get(element_data, "for_id") or self._get(element_data, "forId")
            )
            session.add(element)
            session.commit()

    async def get_element(self, element_id: str):
        with self.SessionLocal() as session:
            el = session.query(DBElement).filter(DBElement.id == element_id).first()
            if el:
                return {
                    "id": el.id,
                    "threadId": el.threadId,
                    "type": el.type,
                    "url": el.url,
                    "chainlitKey": el.chainlitKey,
                    "name": el.name,
                    "display": el.display,
                    "objectKey": el.objectKey,
                    "size": el.size,
                    "mime": el.mime,
                    "path": el.path,
                    "language": el.language,
                    "forId": el.forId
                }
        return None

    async def delete_element(self, element_id: str):
        with self.SessionLocal() as session:
            session.query(DBElement).filter(DBElement.id == element_id).delete()
            session.commit()

    # --- FEEDBACK ---
    async def upsert_feedback(self, feedback: Any):
        with self.SessionLocal() as session:
            fb_id = self._get(feedback, "id") or str(uuid.uuid4())
            existing = session.query(DBFeedback).filter(DBFeedback.id == fb_id).first()
            
            if existing:
                existing.value = self._get(feedback, "value")
                existing.comment = self._get(feedback, "comment")
            else:
                new_fb = DBFeedback(
                    id=fb_id,
                    forId=self._get(feedback, "forId"),
                    value=self._get(feedback, "value"),
                    comment=self._get(feedback, "comment")
                )
                session.add(new_fb)
            session.commit()
            return fb_id

    async def delete_feedback(self, feedback_id: str):
        with self.SessionLocal() as session:
            session.query(DBFeedback).filter(DBFeedback.id == feedback_id).delete()
            session.commit()

    # --- USER ---
    async def get_user(self, identifier: str):
        with self.SessionLocal() as session:
            user = session.query(DBUser).filter(DBUser.identifier == identifier).first()
            if user:
                return {"id": user.id, "identifier": user.identifier, "metadata": user.metadata_}
        return None

    async def create_user(self, user: Any):
        with self.SessionLocal() as session:
            # Check if exists
            identifier = self._get(user, "identifier")
            existing = session.query(DBUser).filter(DBUser.identifier == identifier).first()
            if not existing:
                db_user = DBUser(
                    id=self._get(user, "id") or str(uuid.uuid4()),
                    identifier=identifier,
                    metadata_=self._get(user, "metadata")
                )
                session.add(db_user)
                session.commit()
                return {"id": db_user.id, "identifier": db_user.identifier, "metadata": db_user.metadata_}
            return {"id": existing.id, "identifier": existing.identifier, "metadata": existing.metadata_}

    # --- THREADS ---
    async def get_thread(self, thread_id: str):
        with self.SessionLocal() as session:
            thread = session.query(DBThread).filter(DBThread.id == thread_id).first()
            if not thread:
                return None
            
            steps = session.query(DBStep).filter(DBStep.threadId == thread_id).order_by(DBStep.createdAt).all()
            steps_list = []
            for s in steps:
                steps_list.append({
                    "id": s.id,
                    "name": s.name,
                    "type": s.type,
                    "threadId": s.threadId,
                    "parentId": s.parentId,
                    "input": s.input,
                    "output": s.output,
                    "createdAt": s.createdAt,
                    "feedback": None 
                })
            
            # Fetch elements too? Usually handled separately but good to know.
            
            return {
                "id": thread.id,
                "createdAt": thread.createdAt,
                "name": thread.name,
                "userId": thread.userId,
                "userIdentifier": thread.userIdentifier,
                "tags": thread.tags,
                "metadata": thread.metadata_,
                "steps": steps_list
            }

    async def update_thread(self, thread_id: str, name: Optional[str] = None, user_id: Optional[str] = None, metadata: Optional[Dict] = None, tags: Optional[List[str]] = None):
        with self.SessionLocal() as session:
            thread = session.query(DBThread).filter(DBThread.id == thread_id).first()
            if thread:
                if name is not None: thread.name = name
                if user_id is not None: thread.userId = user_id
                if metadata is not None: thread.metadata_ = metadata
                if tags is not None: thread.tags = tags
                session.commit()

    async def list_threads(self, pagination: Any, filter: ThreadFilter) -> PaginatedResponse:
        with self.SessionLocal() as session:
            query = session.query(DBThread)
            if filter.userIdentifier:
                query = query.filter(DBThread.userIdentifier == filter.userIdentifier)
            if filter.search:
                query = query.filter(DBThread.name.contains(filter.search)) # Simple text search
            if filter.feedback:
                # Joining steps and feedback is complex, skipping for basic sqlite implementation
                pass

            # Simple pagination
            total = query.count()
            # Default sort desc by createdAt
            query = query.order_by(DBThread.createdAt.desc())
            
            threads = query.limit(pagination.first).offset(0).all() # simplified offset
            
            data = []
            for t in threads:
                data.append({
                    "id": t.id,
                    "createdAt": t.createdAt,
                    "name": t.name,
                    "userId": t.userId,
                    "userIdentifier": t.userIdentifier,
                    "tags": t.tags,
                    "metadata": t.metadata_
                })
            
            return PaginatedResponse(data=data, pageInfo={"hasNextPage": False, "endCursor": None})

    async def delete_thread(self, thread_id: str):
        with self.SessionLocal() as session:
            session.query(DBStep).filter(DBStep.threadId == thread_id).delete()
            session.query(DBElement).filter(DBElement.threadId == thread_id).delete()
            session.query(DBThread).filter(DBThread.id == thread_id).delete()
            session.commit()

    # --- STEPS ---
    async def create_step(self, step_data: Any):
        with self.SessionLocal() as session:
            step = DBStep(
                id=self._get(step_data, "id"),
                name=self._get(step_data, "name"),
                type=self._get(step_data, "type"),
                threadId=self._get(step_data, "threadId") or self._get(step_data, "thread_id"),
                parentId=self._get(step_data, "parentId") or self._get(step_data, "parent_id"),
                input=str(self._get(step_data, "input") or ""),
                output=str(self._get(step_data, "output") or ""),
                createdAt=self._get(step_data, "createdAt") or self._get(step_data, "created_at"),
                metadata_=self._get(step_data, "metadata"),
                generation=self._get(step_data, "generation")
            )
            session.add(step)
            session.commit()

    async def update_step(self, step_data: Any):
        with self.SessionLocal() as session:
            step_id = self._get(step_data, "id")
            step = session.query(DBStep).filter(DBStep.id == step_id).first()
            if step:
                if self._get(step_data, "output") is not None: 
                    step.output = str(self._get(step_data, "output"))
                if self._get(step_data, "input") is not None: 
                    step.input = str(self._get(step_data, "input"))
                session.commit()
    
    async def delete_step(self, step_id: str):
         with self.SessionLocal() as session:
            session.query(DBStep).filter(DBStep.id == step_id).delete()
            session.commit()
