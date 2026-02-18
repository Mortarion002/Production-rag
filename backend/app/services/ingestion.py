import os
import shutil
import tempfile
import pathlib
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from app.config import settings

# Initialize Qdrant Client
qdrant_client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)

# Ensure collection exists
try:
    qdrant_client.get_collection(settings.QDRANT_COLLECTION_NAME)
except Exception:
    qdrant_client.create_collection(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        vectors_config=rest.VectorParams(
            size=1536, # text-embedding-3-small dimension
            distance=rest.Distance.COSINE,
        ),
    )

# Initialize Embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=settings.OPENAI_API_KEY)

# Initialize Vector Store
# UPDATED: Use QdrantVectorStore and 'embedding' parameter (singular)
vectorstore = QdrantVectorStore(
    client=qdrant_client,
    collection_name=settings.QDRANT_COLLECTION_NAME,
    embedding=embeddings,
)

def ingest_text(text: str, metadata: dict = None):
    """
    Ingests raw text, chunks it, and stores it in Qdrant.
    """
    if metadata is None:
        metadata = {}
    
    # 1. Chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )
    
    docs = [Document(page_content=text, metadata=metadata)]
    split_docs = text_splitter.split_documents(docs)
    
    # 2. Indexing
    vectorstore.add_documents(split_docs)
    
    return len(split_docs)

def ingest_file(file_path: str, original_filename: str):
    """
    Ingests a file (PDF, TXT, MD), chunks it, and stores it in Qdrant.
    """
    file_ext = pathlib.Path(original_filename).suffix.lower()
    
    if file_ext == ".pdf":
        loader = PyPDFLoader(file_path)
    else:
        # Default to TextLoader for .txt, .md, etc.
        loader = TextLoader(file_path, autodetect_encoding=True)
        
    docs = loader.load()
    
    # Add metadata
    for doc in docs:
        doc.metadata["filename"] = original_filename
        
    # 1. Chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )
    
    split_docs = text_splitter.split_documents(docs)
    
    # 2. Indexing
    if split_docs:
        vectorstore.add_documents(split_docs)
    
    return len(split_docs)

def get_retriever():
    """Returns the vector store retriever."""
    return vectorstore.as_retriever(search_kwargs={"k": 5})