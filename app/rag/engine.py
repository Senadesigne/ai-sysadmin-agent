import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from llama_parse import LlamaParse
from dotenv import load_dotenv

load_dotenv()

class RagEngine:
    def __init__(self, persist_directory: str = "./app/data/chroma_db"):
        self.persist_directory = persist_directory
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
             print("WARNING: GOOGLE_API_KEY not found. Embeddings will fail.")

        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key
        )
        
        # Initialize ChromaDB
        self.vector_store = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings
        )

    def ingest_document(self, pdf_path: str) -> int:
        """
        Ingests a PDF document into the vector store using LlamaParse.
        Returns the number of chunks added.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"File not found: {pdf_path}")

        print(f"Starting parsing of {pdf_path} with LlamaParse...")
        
        try:
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
            print(f"Error during ingestion: {e}")
            raise e

    def ingest_markdown(self, file_path: str) -> int:
        """
        Ingests a Markdown file into the vector store.
        Simple text reading, no external parser needed for basic MD.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        print(f"Reading markdown file: {file_path}...")
        try:
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
            print(f"Error ingesting markdown: {e}")
            raise e

    def query(self, question: str, k: int = 3) -> list[str]:
        """
        Retrieves relevant document chunks for the question.
        Returns a list of strings (content of the chunks).
        """
        results = self.vector_store.similarity_search(question, k=k)
        return [doc.page_content for doc in results]
