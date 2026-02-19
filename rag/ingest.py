# rag/ingest.py
from __future__ import annotations

from pathlib import Path
from typing import List

from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

# Local embeddings (no Google API)
from langchain_huggingface import HuggingFaceEmbeddings


DOCS_DIR = Path("docs")
INDEX_DIR = Path("rag_index")

# ✅ Restrict ingestion to ONLY these “real knowledge” docs (everything else is ignored)
ALLOWED_FILES = {
    "architecture.md",
    "onboarding_guide.md",
    "offboarding_guide.md",
    "security.md",
}


def ingest() -> None:
    if not DOCS_DIR.exists():
        raise FileNotFoundError("docs/ folder not found. Create docs/*.md first.")

    loaded_docs = []
    ingested_files = []
    skipped_files = []

    for file in sorted(DOCS_DIR.glob("*.md")):
        if file.name.lower() not in ALLOWED_FILES:
            skipped_files.append(file.name)
            continue

        loader = TextLoader(str(file), encoding="utf-8")
        docs = loader.load()
        loaded_docs.extend(docs)
        ingested_files.append(file.name)

    if not loaded_docs:
        raise ValueError(
            "No allowed docs were ingested.\n"
            f"Expected these files (exact names, lowercase): {sorted(ALLOWED_FILES)}\n"
            f"Found these .md files: {[p.name for p in DOCS_DIR.glob('*.md')]}"
        )

    # --- chunking ---
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=120)
    chunks = splitter.split_documents(loaded_docs)

    # --- Local embeddings ---
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # --- build + persist FAISS index ---
    vectorstore = FAISS.from_documents(chunks, embeddings)
    INDEX_DIR.mkdir(exist_ok=True)
    vectorstore.save_local(str(INDEX_DIR))

    print(f"✅ RAG index built with {len(chunks)} chunks from {len(ingested_files)} allowed docs.")
    print(f"✅ Saved to: {INDEX_DIR}/")
    print(f"✅ Ingested: {ingested_files}")
    if skipped_files:
        print(f"Skipped (not in ALLOWED_FILES): {skipped_files}")


if __name__ == "__main__":
    ingest()
