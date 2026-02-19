# agents/onboarding_agent.py
"""
Onboarding Agent = "Context Grounding" Agent (RAG)

Responsibilities:
- Retrieve relevant internal context from the FAISS RAG index for the current request.
- IMPORTANT RULE:
  - If a user question exists -> retrieve using THAT question (especially for /chat).
  - Otherwise -> use role + action as a fallback query (useful for lifecycle runs).
- Write to state:
    state["rag_context_preview"] = "<string>"
    state["rag_sources"] = {"primary":[...], "related":[...]}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _safe_str(x: Any) -> str:
    return "" if x is None else str(x)


def _build_query(state: Dict[str, Any]) -> str:
    """
    Priority:
      1) explicit question (best for chat + accurate retrieval)
      2) fallback to role/action grounding
    """
    question = _safe_str(state.get("question")).strip()
    if question:
        return question

    role = _safe_str(state.get("role") or "Employee").strip()
    action = _safe_str(state.get("action") or "onboard").strip()
    name = _safe_str(state.get("name") or "User").strip()

    # A lightweight default query when no explicit question is given
    # (useful for lifecycle runs that may not include a question)
    return f"{action} process for role {role}. Key docs, access, steps, and contacts for {name}."


def onboarding_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mutates and returns state.
    """
    query = _build_query(state)
    name = _safe_str(state.get("name") or "User").strip()
    role = _safe_str(state.get("role") or "Employee").strip()
    action = _safe_str(state.get("action") or "onboard").strip()

    print("🧠 Onboarding Agent: role/context grounding via RAG")
    print(f"👤 {name} | Role: {role} | Action: {action}")

    try:
        from rag.retriever import retrieve_context  # must exist in rag/retriever.py

        # retrieve_context returns:
        # {
        #   "context": "...",
        #   "primary_sources": [...],
        #   "related_sources": [...],
        #   "docs": [...],
        #   "bias_file": "...",
        #   "k": ...
        # }
        out = retrieve_context(query, k=6)

        context = (out.get("context") or "").strip()

        primary = out.get("primary_sources", []) or []
        related = out.get("related_sources", []) or []

        # normalize to strings, dedupe preserving order
        def _dedupe(xs: List[Any]) -> List[str]:
            seen = set()
            res: List[str] = []
            for x in xs:
                s = _safe_str(x).strip()
                if not s or s in seen:
                    continue
                seen.add(s)
                res.append(s)
            return res

        primary = _dedupe(primary)
        related = _dedupe(related)

        # Preview: keep it readable in logs + UI
        preview = context
        if len(preview) > 1200:
            preview = preview[:1200] + "\n...\n"

        state["rag_context_preview"] = preview

        # Unified shape used by chat_agent + API response
        state["rag_sources"] = {
            "primary": primary,
            "related": related,
        }

        print("📚 Retrieved internal context (RAG):")
        if preview:
            # print a short preview
            print(preview[:400] + ("\n..." if len(preview) > 400 else ""))
        else:
            print("(no context found)")

        print(f"📌 Primary sources: {primary}")
        print(f"📎 Related sources: {related}")

    except Exception as e:
        # Never crash the workflow due to RAG failure — just store the error
        state["rag_context_preview"] = ""
        state["rag_sources"] = {"primary": [], "related": []}
        state["rag_error"] = str(e)

        print("❌ RAG retrieval failed:", str(e))

    return state
