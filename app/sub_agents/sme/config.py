"""
Configuration settings for the SME (RAG) Agent.

These settings are used by the BigQuery vector search tools.
Vertex AI is used only for generating embeddings (not Spanner RAG).
"""

import os
from dotenv import load_dotenv

# Load environment variables (safe even if __init__.py already did this)
load_dotenv()

# Vertex AI settings (for embedding generation only)
PROJECT_ID: str | None = os.environ.get("GOOGLE_CLOUD_PROJECT", "ape-ds")
LOCATION: str | None = os.environ.get("HR_RAG_LOCATION", "us-central1")

# BigQuery settings (storage backend)
BQ_DATASET: str = os.environ.get("BQ_RAG_DATASET", "apex_rag")
BQ_EMBEDDINGS_TABLE: str = f"{PROJECT_ID}.{BQ_DATASET}.document_embeddings"
BQ_METADATA_TABLE: str = f"{PROJECT_ID}.{BQ_DATASET}.document_metadata"

# Corpus defaults (current domain = HR handbook; can add more later)
HR_CORPUS_NAME: str = os.environ.get("HR_CORPUS_NAME", "m1_hr_handbook")

# Chunking settings (for document processing)
DEFAULT_CHUNK_SIZE: int = int(os.environ.get("HR_RAG_CHUNK_SIZE", 512))
DEFAULT_CHUNK_OVERLAP: int = int(os.environ.get("HR_RAG_CHUNK_OVERLAP", 100))

# Search settings
DEFAULT_TOP_K: int = int(os.environ.get("HR_RAG_TOP_K", 3))
DEFAULT_SIMILARITY_THRESHOLD: float = float(os.environ.get("HR_RAG_SIMILARITY_THRESHOLD", 0.7))

# Vertex AI Embedding Model
DEFAULT_EMBEDDING_MODEL: str = os.environ.get(
    "HR_RAG_EMBEDDING_MODEL", "text-embedding-005"
)
EMBEDDING_DIMENSIONS: int = 768  # text-embedding-005 outputs 768 dimensions

# Rate limiting for batch processing
DEFAULT_EMBEDDING_REQUESTS_PER_MIN: int = int(
    os.environ.get("HR_RAG_EMBEDDING_RPM", 1000)
)

# Contact (used in prompts/tools)
HR_PHONE: str = os.environ.get("HR_PHONE", "929-877-9259")
