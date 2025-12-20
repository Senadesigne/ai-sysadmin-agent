import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.rag.engine import get_rag_engine
from app.config import settings

def main():
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <filename>")
        print("  <filename> should be inside app/knowledge_base/")
        sys.exit(1)

    # Check if RAG is enabled
    if not settings.RAG_ENABLED:
        print("ERROR: RAG is disabled (RAG_ENABLED=false in .env)")
        print("Set RAG_ENABLED=true in .env to enable document ingestion")
        sys.exit(1)

    filename = sys.argv[1]
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'app', 'knowledge_base')
    file_path = os.path.join(base_dir, filename)

    print(f"Targeting file: {file_path}")

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)

    engine = get_rag_engine()
    
    try:
        if filename.lower().endswith('.pdf'):
            print("Detected PDF. Using Document Ingestion...")
            count = engine.ingest_document(file_path)
        elif filename.lower().endswith('.md'):
            print("Detected Markdown. Using Markdown Ingestion...")
            count = engine.ingest_markdown(file_path)
        else:
            print("Unknown file type. Only .pdf and .md supported.")
            sys.exit(1)

        print(f"DONE. Ingested {count} chunks.")
    except Exception as e:
        print(f"Ingestion FAILED: {e}")

if __name__ == "__main__":
    main()
