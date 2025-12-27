import os
from pathlib import Path
from typing import List, Optional, Dict, Any

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from llama_parse import LlamaParse

from app.config import settings

# Environment variables are loaded in app.config.settings


def _emit_rag_event(event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
    """
    Emit RAG event if ENABLE_EVENTS=true.
    Fail-safe: must never crash the app.
    """
    if not settings.ENABLE_EVENTS:
        return
    
    try:
        from app.core.events import get_emitter
        emitter = get_emitter()
        emitter.emit(event_type, data or {})
    except Exception:
        pass  # Events must never crash the app


class NullRagEngine:
    """
    No-op RAG engine that returns empty results when RAG is disabled or offline.
    Implements the same interface as RagEngine for compatibility.
    """
    
    def __init__(self, reason: str = "disabled"):
        self.is_enabled = False
        self.fallback_reason = reason
        print(f"INFO: RAG is {reason}, using NullRagEngine (no-op)")
        
        # Emit fallback event
        _emit_rag_event("rag_fallback", {
            "reason": "offline_mode" if reason == "offline" else "disabled",
            "component": "NullRagEngine"
        })
    
    def ingest_document(self, pdf_path: str) -> int:
        """No-op document ingestion."""
        print(f"INFO: RAG {self.fallback_reason} - skipping document ingestion for {pdf_path}")
        return 0
    
    def ingest_markdown(self, file_path: str) -> int:
        """No-op markdown ingestion."""
        print(f"INFO: RAG {self.fallback_reason} - skipping markdown ingestion for {file_path}")
        return 0
    
    def query(self, question: str, k: int = 3) -> List[str]:
        """Return empty context when RAG is disabled."""
        return []


class RagEngine:
    def __init__(self, persist_directory: str | None = None):
        self.is_enabled = True
        
        try:
            settings.ensure_data_dirs()

            persist_path = Path(persist_directory) if persist_directory else settings.CHROMA_DIR
            self.persist_directory = str(persist_path)
            
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key or api_key.startswith("ovdje_ide") or api_key.strip() == "":
                raise ValueError("GOOGLE_API_KEY not configured for RAG embeddings")

            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=api_key
            )
            
            # Initialize ChromaDB
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
            print("INFO: RAG engine initialized successfully")
            
        except Exception as e:
            error_type = type(e).__name__
            print(f"WARNING: Failed to initialize RAG engine: {e}")
            print("RAG functionality will be disabled for this session")
            
            # Emit fallback event
            _emit_rag_event("rag_fallback", {
                "reason": "init_error",
                "error_type": error_type,
                "component": "RagEngine"
            })
            
            self.is_enabled = False
            self.embeddings = None
            self.vector_store = None

    def ingest_document(self, pdf_path: str) -> int:
        """
        Ingests a PDF document into the vector store using LlamaParse.
        Returns the number of chunks added.
        Never crashes - returns 0 on error.
        """
        if not self.is_enabled:
            print(f"WARNING: RAG engine not properly initialized - skipping document ingestion for {pdf_path}")
            return 0
            
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"File not found: {pdf_path}")

            print(f"Starting parsing of {pdf_path} with LlamaParse...")
            
            # LlamaParse extraction (markdown mode is excellent for tables)
            parser = LlamaParse(
                result_type="markdown",
                verbose=True,
                language="en"
            )
            json_objs = parser.load_data(pdf_path)
            
            # Convert LlamaIndex documents to LangChain Documents
            documents = []
            for obj in json_objs:
                # obj is usually a LlamaIndex Document object, we need its text
                text = obj.text
                metadata = obj.metadata or {}
                metadata["source"] = pdf_path
                documents.append(Document(page_content=text, metadata=metadata))
                
            # Chunking
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=2000,
                chunk_overlap=200
            )
            chunks = text_splitter.split_documents(documents)
            
            # Add to Vector Store
            if chunks:
                self.vector_store.add_documents(chunks)
                self.vector_store.persist()
                print(f"Successfully ingested {len(chunks)} chunks from {pdf_path}")
                return len(chunks)
            return 0
            
        except Exception as e:
            error_type = type(e).__name__
            print(f"ERROR: Document ingestion failed: {e}")
            
            # Emit fallback event
            _emit_rag_event("rag_fallback", {
                "reason": "ingest_error",
                "error_type": error_type,
                "operation": "ingest_document"
            })
            
            return 0

    def ingest_markdown(self, file_path: str) -> int:
        """
        Ingests a Markdown file into the vector store.
        Simple text reading, no external parser needed for basic MD.
        Never crashes - returns 0 on error.
        """
        if not self.is_enabled:
            print(f"WARNING: RAG engine not properly initialized - skipping markdown ingestion for {file_path}")
            return 0
            
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            print(f"Reading markdown file: {file_path}...")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content:
                print("File is empty.")
                return 0

            # Create a single document (we rely on splitter to chunk it)
            metadata = {"source": file_path, "type": "markdown"}
            doc = Document(page_content=content, metadata=metadata)
            
            # Chunking
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            chunks = text_splitter.split_documents([doc])
            
            # Add to Vector Store
            if chunks:
                self.vector_store.add_documents(chunks)
                self.vector_store.persist()
                print(f"Successfully ingested {len(chunks)} chunks from {file_path}")
                return len(chunks)
            return 0

        except Exception as e:
            error_type = type(e).__name__
            print(f"ERROR: Markdown ingestion failed: {e}")
            
            # Emit fallback event
            _emit_rag_event("rag_fallback", {
                "reason": "ingest_error",
                "error_type": error_type,
                "operation": "ingest_markdown"
            })
            
            return 0

    def query(self, question: str, k: int = 3) -> List[str]:
        """
        Retrieves relevant document chunks for the question.
        Returns a list of strings (content of the chunks).
        Never crashes - returns [] on error.
        """
        if not self.is_enabled:
            return []
        
        try:
            # Emit query event
            _emit_rag_event("rag_query", {
                "operation": "query",
                "k": k
            })
            
            results = self.vector_store.similarity_search(question, k=k)
            return [doc.page_content for doc in results]
            
        except Exception as e:
            error_type = type(e).__name__
            print(f"ERROR: RAG query failed: {e}")
            
            # Emit fallback event
            _emit_rag_event("rag_fallback", {
                "reason": "query_error",
                "error_type": error_type,
                "operation": "query"
            })
            
            return []


def get_rag_engine(persist_directory: str | None = None):
    """
    Factory function to get the appropriate RAG engine based on configuration.
    Returns NullRagEngine if RAG is disabled or OFFLINE_MODE is enabled, otherwise RagEngine.
    """
    if settings.OFFLINE_MODE:
        return NullRagEngine(reason="offline")
    
    if not settings.RAG_ENABLED:
        return NullRagEngine(reason="disabled")
    
    return RagEngine(persist_directory)
