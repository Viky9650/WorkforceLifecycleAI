# rag/retriever.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# Where rag/ingest.py saves the FAISS index
RAG_INDEX_DIR = Path("rag_index")

# Default top-k
DEFAULT_K = 8

# Keyword → preferred source file (simple, effective routing)
DOC_BIAS_RULES: List[Tuple[str, str]] = [
    ("onboarding", "onboarding_guide.md"),
    ("onboard", "onboarding_guide.md"),
    ("offboarding", "offboarding_guide.md"),
    ("offboard", "offboarding_guide.md"),
    ("security", "security.md"),
    ("rbac", "security.md"),
    ("access", "security.md"),
    ("permission", "security.md"),
    ("permissions", "security.md"),
    ("iam", "security.md"),
]

# Cache so we don't reload FAISS on every request
_STORE: Optional[FAISS] = None


def _load_vector_store() -> FAISS:
    """
    Load the FAISS vector store from disk.
    IMPORTANT: Must use the same embedding model as rag/ingest.py.
    """
    global _STORE
    if _STORE is not None:
        return _STORE

    if not RAG_INDEX_DIR.exists():
        raise FileNotFoundError(
            f"RAG index not found at: {RAG_INDEX_DIR}/. Run: python -m rag.ingest"
        )

    # ✅ Local embeddings (must match ingest.py)
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    _STORE = FAISS.load_local(
        str(RAG_INDEX_DIR),
        embeddings,
        allow_dangerous_deserialization=True,
    )
    return _STORE


def _infer_bias_filename(query: str) -> Optional[str]:
    q = (query or "").lower()
    for keyword, filename in DOC_BIAS_RULES:
        if keyword in q:
            return filename
    return None


def _normalize_source(src: Any) -> str:
    """
    In ingest, metadata["source"] might be:
      - "onboarding_guide.md"
      - "docs/onboarding_guide.md"
    We'll normalize to just the filename.
    """
    s = str(src or "unknown").replace("\\", "/")
    return s.split("/")[-1]


def retrieve_context(query: str, k: int = DEFAULT_K) -> Dict[str, Any]:
    """
    Retrieve relevant internal context for a query.

    Returns:
      {
        "context": "<combined context text>",
        "primary_sources": [...],
        "related_sources": [...],
        "docs": [{"source": "...", "content": "...", "score": ...}, ...],
        "bias_file": "<preferred file or None>",
        "k": k
      }

    Behavior:
    - pulls candidates (k*3, min 12)
    - applies doc-bias (onboarding/offboarding/security) if possible
    - falls back if bias filter matches nothing
    - returns combined context + source lists
    """
    store = _load_vector_store()

    # 1) Pull more candidates than needed; then filter down
    candidate_k = max(k * 3, 12)
    candidates = store.similarity_search_with_score(query, k=candidate_k)

    # 2) Apply bias filter
    bias_file = _infer_bias_filename(query)
    filtered: List[Tuple[Any, float]] = []

    if bias_file:
        for doc, score in candidates:
            src = _normalize_source((doc.metadata or {}).get("source", ""))
            if src == bias_file:
                filtered.append((doc, score))

        # If nothing matched bias, fallback to unfiltered candidates
        if not filtered:
            filtered = candidates
    else:
        filtered = candidates

    # 3) Take top-k
    top = filtered[:k]

    # 4) Build response
    docs_out: List[Dict[str, Any]] = []
    sources_in_order: List[str] = []
    seen = set()
    context_blocks: List[str] = []

    for doc, score in top:
        src = _normalize_source((doc.metadata or {}).get("source", "unknown"))
        text = (doc.page_content or "").strip()
        if not text:
            continue

        context_blocks.append(f"---\nSOURCE: {src}\n{text}")
        docs_out.append({"source": src, "content": text, "score": float(score)})

        if src not in seen:
            seen.add(src)
            sources_in_order.append(src)

    return {
        "context": "\n\n".join(context_blocks).strip(),
        "primary_sources": sources_in_order[:2],
        "related_sources": sources_in_order[2:],
        "docs": docs_out,
        "bias_file": bias_file,
        "k": k,
    }
