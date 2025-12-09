"""
Configuration settings for the SME (RAG) Agent.

These settings are used by the various RAG tools.
Vertex AI initialization is performed in the package's __init__.py (per your setup).
"""

import os
from dotenv import load_dotenv

# Load environment variables (safe even if __init__.py already did this)
load_dotenv()

# Vertex AI settings
PROJECT_ID: str | None = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION: str | None = os.environ.get("HR_RAG_LOCATION")

# Corpus defaults (current domain = HR handbook; can add more later)
HR_CORPUS_NAME: str = os.environ.get("HR_CORPUS_NAME", "m1_hr_handbook")

# RAG settings
DEFAULT_CHUNK_SIZE: int = int(os.environ.get("HR_RAG_CHUNK_SIZE", 512))
DEFAULT_CHUNK_OVERLAP: int = int(os.environ.get("HR_RAG_CHUNK_OVERLAP", 100))
DEFAULT_TOP_K: int = int(os.environ.get("HR_RAG_TOP_K", 3))
DEFAULT_DISTANCE_THRESHOLD: float = float(os.environ.get("HR_RAG_DISTANCE_THRESHOLD", 0.5))
DEFAULT_EMBEDDING_MODEL: str = os.environ.get(
    "HR_RAG_EMBEDDING_MODEL", "publishers/google/models/text-embedding-005"
)
DEFAULT_EMBEDDING_REQUESTS_PER_MIN: int = int(
    os.environ.get("HR_RAG_EMBEDDING_RPM", 1000)  # your requested default
)

# Contact (used in prompts/tools)
HR_PHONE: str = os.environ.get("HR_PHONE", "718.370.6771")
