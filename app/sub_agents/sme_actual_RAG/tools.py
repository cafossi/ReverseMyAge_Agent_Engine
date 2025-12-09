"""
SME Tools — unified Vertex AI RAG + domain helpers (starting with HR handbook).
"""

from __future__ import annotations
import logging, os, re
from typing import Dict, List
from dotenv import load_dotenv
from vertexai import rag
from google.adk.tools.tool_context import ToolContext

from vertexai import init as vinit

from .config import (
    PROJECT_ID,
    LOCATION,
    HR_CORPUS_NAME,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_TOP_K,
    DEFAULT_DISTANCE_THRESHOLD,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_EMBEDDING_REQUESTS_PER_MIN,
    HR_PHONE,
)

load_dotenv()

logger = logging.getLogger("sme_tools")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# ---------- force the SME tools to initialize Vertex in HR_RAG_LOCATION ----------

_vertex_initialized_for: str | None = None

def _ensure_vertex_region():
    """
    Initialize Vertex SDK for the SME/RAG region (HR_RAG_LOCATION or fallback).
    Ensures Amanda's RAG Engine calls don't inherit the global app region.
    """
    global _vertex_initialized_for
    if _vertex_initialized_for == LOCATION:
        return
    if not PROJECT_ID or not LOCATION:
        raise EnvironmentError("Missing PROJECT_ID or LOCATION for SME/RAG. Check env.")
    vinit(project=PROJECT_ID, location=LOCATION)
    _vertex_initialized_for = LOCATION


# ---------- Utilities ----------

def get_corpus_resource_name(corpus_name: str) -> str:
    _ensure_vertex_region()  # ✅
    if not corpus_name:
        raise ValueError("corpus_name is required")
    # already a resource name?
    if re.match(r"^projects/[^/]+/locations/[^/]+/ragCorpora/[^/]+$", corpus_name):
        return corpus_name
    # try resolve by display_name
    try:
        for c in rag.list_corpora():
            if getattr(c, "display_name", None) == corpus_name:
                return c.name
    except Exception:
        pass
    # fallback: construct
    if not PROJECT_ID or not LOCATION:
        raise EnvironmentError("PROJECT_ID and LOCATION must be set")
    corpus_id = re.sub(r"[^a-zA-Z0-9_-]", "_", corpus_name.split("/")[-1])
    return f"projects/{PROJECT_ID}/locations/{LOCATION}/ragCorpora/{corpus_id}"


# ---------- Utilities ----------

def check_corpus_exists(corpus_name: str, tool_context: ToolContext) -> bool:
    _ensure_vertex_region()  # ✅
    try:
        corpus_res = get_corpus_resource_name(corpus_name)
        for c in rag.list_corpora():
            if c.name == corpus_res or getattr(c, "display_name", None) == corpus_name:
                tool_context.state[f"corpus_exists_{corpus_name}"] = True
                tool_context.state.setdefault("current_corpus", corpus_name)
                return True
        return False
    except Exception as e:
        logger.error(f"Error checking corpus existence: {e}")
        return False



# ---------- Generic RAG admin/query ----------

def list_corpora() -> dict:
    _ensure_vertex_region()  # ✅
    try:
        corpora = rag.list_corpora()
        data = [{
            "resource_name": c.name,
            "display_name": getattr(c, "display_name", ""),
            "create_time": str(getattr(c, "create_time", "")),
            "update_time": str(getattr(c, "update_time", "")),
        } for c in corpora]
        return {"status": "success", "corpora": data, "count": len(data), "region": LOCATION}
    except Exception as e:
        return {"status": "error", "message": str(e), "corpora": [], "region": LOCATION}


# ---------- Generic RAG admin/query ----------

def create_corpus(corpus_name: str, tool_context: ToolContext) -> dict:
    _ensure_vertex_region()  # ✅
    if check_corpus_exists(corpus_name, tool_context):
        return {"status": "info", "message": f"Corpus '{corpus_name}' already exists", "region": LOCATION}
    try:
        cfg = rag.RagEmbeddingModelConfig(
            vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
                publisher_model=DEFAULT_EMBEDDING_MODEL
            )
        )
        corpus = rag.create_corpus(
            display_name=re.sub(r"[^a-zA-Z0-9_-]", "_", corpus_name),
            backend_config=rag.RagVectorDbConfig(rag_embedding_model_config=cfg),
        )
        tool_context.state[f"corpus_exists_{corpus_name}"] = True
        tool_context.state["current_corpus"] = corpus_name
        return {"status": "success", "message": f"Created corpus '{corpus_name}'", "name": corpus.name, "region": LOCATION}
    except Exception as e:
        return {"status": "error", "message": f"Error creating corpus: {e}", "region": LOCATION}


# ---------- Generic RAG admin/query ----------

def add_data(corpus_name: str, paths: List[str], tool_context: ToolContext) -> dict:
    _ensure_vertex_region()  # ✅
    if not paths or not all(isinstance(p, str) and p for p in paths):
        return {"status": "error", "message": "paths must be a non-empty list of strings", "region": LOCATION}
    try:
        corpus_res = get_corpus_resource_name(corpus_name or HR_CORPUS_NAME)
        tx = rag.TransformationConfig(
            chunking_config=rag.ChunkingConfig(
                chunk_size=DEFAULT_CHUNK_SIZE,
                chunk_overlap=DEFAULT_CHUNK_OVERLAP,
            )
        )
        res = rag.import_files(
            corpus_res,
            paths,
            transformation_config=tx,
            max_embedding_requests_per_min=DEFAULT_EMBEDDING_REQUESTS_PER_MIN,
        )
        return {"status": "success", "message": f"Added {res.imported_rag_files_count} file(s)", "region": LOCATION}
    except Exception as e:
        return {"status": "error", "message": f"Error adding data: {e}", "region": LOCATION}



# ---------- Generic RAG admin/query ----------

def get_corpus_info(corpus_name: str, tool_context: ToolContext) -> dict:
    _ensure_vertex_region()  # ✅
    try:
        corpus_res = get_corpus_resource_name(corpus_name)
        files = rag.list_files(corpus_res)
        data = [{
            "id": f.name.split("/")[-1],
            "display_name": getattr(f, "display_name", ""),
            "source_uri": getattr(f, "source_uri", ""),
            "create_time": str(getattr(f, "create_time", "")),
            "update_time": str(getattr(f, "update_time", "")),
        } for f in files]
        return {"status": "success", "count": len(data), "files": data, "region": LOCATION}
    except Exception as e:
        return {"status": "error", "message": f"Error getting corpus info: {e}", "region": LOCATION}


# ---------- Generic RAG admin/query ----------


def delete_document(corpus_name: str, document_id: str, tool_context: ToolContext) -> dict:
    _ensure_vertex_region()  # ✅
    if not document_id:
        return {"status": "error", "message": "document_id is required", "region": LOCATION}
    try:
        rag.delete_file(f"{get_corpus_resource_name(corpus_name)}/ragFiles/{document_id}")
        return {"status": "success", "message": f"Deleted doc {document_id}", "region": LOCATION}
    except Exception as e:
        return {"status": "error", "message": f"Error deleting document: {e}", "region": LOCATION}


# ---------- Generic RAG admin/query ----------


def delete_corpus(corpus_name: str, confirm: bool, tool_context: ToolContext) -> dict:
    _ensure_vertex_region()  # ✅
    if not confirm:
        return {"status": "error", "message": "confirm=True required", "region": LOCATION}
    try:
        rag.delete_corpus(get_corpus_resource_name(corpus_name))
        return {"status": "success", "message": f"Deleted corpus '{corpus_name}'", "region": LOCATION}
    except Exception as e:
        return {"status": "error", "message": f"Error deleting corpus: {e}", "region": LOCATION}



# ---------- Generic RAG query ----------


def rag_query(corpus_name: str, query: str, tool_context: ToolContext) -> dict:
    _ensure_vertex_region()  # ✅
    if not query or not isinstance(query, str):
        return {"status": "error", "message": "query must be a non-empty string", "region": LOCATION}
    try:
        corpus_res = get_corpus_resource_name(corpus_name)
        cfg = rag.RagRetrievalConfig(
            top_k=DEFAULT_TOP_K,
            filter=rag.Filter(vector_distance_threshold=DEFAULT_DISTANCE_THRESHOLD),
        )
        res = rag.retrieval_query(
            rag_resources=[rag.RagResource(rag_corpus=corpus_res)],
            text=query,
            rag_retrieval_config=cfg,
        )
        contexts = [{
            "text": getattr(c, "text", ""),
            "source": getattr(c, "source_display_name", ""),
            "score": getattr(c, "score", 0.0),
        } for c in getattr(res.contexts, "contexts", [])]
        return {
            "status": "success" if contexts else "warning",
            "message": "Results returned" if contexts else f"No results in '{corpus_name}'",
            "results": contexts,
            "count": len(contexts),
            "region": LOCATION,
        }
    except Exception as e:
        logger.error(f"rag_query error: {e}")
        return {"status": "error", "message": f"Error querying corpus: {e}", "region": LOCATION}




# ---------- SME domain wrappers (current: HR handbook) ----------

def query_hr_policy(query: str, tool_context: ToolContext) -> dict:
    return rag_query(HR_CORPUS_NAME, query, tool_context)


def list_available_policies(tool_context: ToolContext) -> dict:
    """Heuristic: surface likely headings from the handbook."""
    try:
        corpus_res = get_corpus_resource_name(HR_CORPUS_NAME)
        res = rag.retrieval_query(
            rag_resources=[rag.RagResource(rag_corpus=corpus_res)],
            text="Table of contents, policy section headings, and summaries.",
            rag_retrieval_config=rag.RagRetrievalConfig(top_k=10),
        )
        sections: List[str] = []
        for ctx in getattr(res.contexts, "contexts", []):
            first = (getattr(ctx, "text", "") or "").strip().splitlines()[0:1]
            candidate = (first[0].strip().upper() if first else "")
            if candidate and candidate not in sections:
                sections.append(candidate)
        return {"status": "success", "sections": sections[:20]}
    except Exception as e:
        return {"status": "error", "message": f"Unable to list sections: {e}", "sections": []}


def get_hr_contact_info() -> dict:
    return {
        "status": "success",
        "hr_phone": HR_PHONE,
        "notes": "If unclear or sensitive (e.g., harassment), escalate directly to HR.",
    }
