# rag/kt_index.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

RAG_INDEX_DIR = Path("rag_index")


def _embeddings():
    # MUST match rag/ingest.py + rag/retriever.py
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def _load_store() -> FAISS:
    if not RAG_INDEX_DIR.exists():
        raise FileNotFoundError("rag_index/ not found. Run: python -m rag.ingest")

    return FAISS.load_local(
        str(RAG_INDEX_DIR),
        _embeddings(),
        allow_dangerous_deserialization=True,
    )


def add_kt_to_index(kt_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adds KT notes into the existing FAISS index.
    This must use the SAME embedding model as the index was built with.
    """
    vs = _load_store()

    # Flatten to text for retrieval
    text = json.dumps(kt_payload, indent=2, ensure_ascii=False)

    doc = Document(
        page_content=text,
        metadata={
            "source": f"{kt_payload.get('employee','employee')}_kt.json",
            "type": "kt",
            "employee": kt_payload.get("employee"),
            "role": kt_payload.get("role"),
            "action": kt_payload.get("action", "offboard"),
        },
    )

    vs.add_documents([doc])
    vs.save_local(str(RAG_INDEX_DIR))

    return {"ok": True, "added": 1, "source": doc.metadata["source"]}
