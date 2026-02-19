# agents/chat_agent.py
"""
Chat Agent (Gemini + RAG + Policy-as-truth)

- Policy questions (roles/access/permissions) -> answer from config/access_policies.yml
- Knowledge questions -> answer from RAG context
- In chat mode, RAG should be retrieved using the user QUESTION (not role/action).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import yaml
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
POLICY_PATH = os.getenv("ACCESS_POLICY_PATH", str(BASE_DIR / "config" / "access_policies.yml"))

GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash-lite")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


# -----------------------------
# Policy helpers
# -----------------------------
ROLE_ALIASES = {
    "devops": "DevOps Engineer",
    "devops engineer": "DevOps Engineer",
    "infra": "Infrastructure Specialist",
    "infrastructure": "Infrastructure Specialist",
    "infrastructure specialist": "Infrastructure Specialist",
    "sre": "SRE",
    "site reliability engineer": "SRE",
    "architect": "Architect",
}

def _load_policies() -> Dict[str, Any]:
    try:
        with open(POLICY_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def list_available_roles() -> List[str]:
    pol = _load_policies()
    roles = [k for k in pol.keys() if isinstance(k, str)]
    return sorted(roles)

def _normalize_role(role: str) -> str:
    r = (role or "").strip()
    if not r:
        return ""
    # normalize via aliases (case-insensitive)
    key = r.lower().strip()
    return ROLE_ALIASES.get(key, r)

def systems_for_role(role: str) -> List[str]:
    pol = _load_policies()
    role = _normalize_role(role)
    role_obj = pol.get(role, {})
    if isinstance(role_obj, dict):
        systems = role_obj.get("systems", [])
        if isinstance(systems, list):
            return [str(s) for s in systems]
    return []

def _extract_role_from_question(q: str) -> Optional[str]:
    ql = (q or "").lower()

    # detect known role keywords in the question
    for key, canonical in ROLE_ALIASES.items():
        # match whole words for short keys like "sre", "infra"
        if re.search(rf"\b{re.escape(key)}\b", ql):
            return canonical

    # Also allow explicit “for <Role Name>”
    m = re.search(r"for\s+([A-Za-z ]+)", q)
    if m:
        candidate = m.group(1).strip()
        # if candidate matches an existing policy role (case-sensitive keys), map it
        pol = _load_policies()
        if candidate in pol:
            return candidate
        # try alias normalization
        return _normalize_role(candidate)

    return None


# -----------------------------
# RAG helpers
# -----------------------------
def _get_rag_from_state(state: Dict[str, Any]) -> Tuple[str, Dict[str, List[str]]]:
    """
    Supports your state format:
      state["rag_context_preview"]
      state["rag_sources"] = {"primary":[...], "related":[...]}   (or)
      state["rag_sources"] = {"primary_sources":[...], "related_sources":[...]}
    """
    context = state.get("rag_context_preview") or ""
    sources = state.get("rag_sources") or {}

    if not isinstance(sources, dict):
        sources = {}

    primary = sources.get("primary") or sources.get("primary_sources") or []
    related = sources.get("related") or sources.get("related_sources") or []

    if not isinstance(primary, list): primary = []
    if not isinstance(related, list): related = []

    return str(context), {"primary": list(primary), "related": list(related)}

def _fallback_retrieve(question: str, k: int = 6) -> Tuple[str, Dict[str, List[str]]]:
    """
    Supports your rag.retriever.py return format:
      {
        "context": "...",
        "primary_sources": [...],
        "related_sources": [...],
      }
    """
    from rag.retriever import retrieve_context  # local import
    out = retrieve_context(question, k=k)

    ctx = out.get("context", "") if isinstance(out, dict) else ""
    primary = out.get("primary_sources", []) if isinstance(out, dict) else []
    related = out.get("related_sources", []) if isinstance(out, dict) else []

    if not isinstance(primary, list): primary = []
    if not isinstance(related, list): related = []

    return str(ctx), {"primary": list(primary), "related": list(related)}


# -----------------------------
# Agent
# -----------------------------
def chat_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    question = (state.get("question") or "").strip()
    name = (state.get("name") or "User").strip()
    state_role = (state.get("role") or "Employee").strip()

    if not question:
        state["chat"] = {
            "enabled": True,
            "question": "",
            "answer": "(no question provided)",
            "sources": [],
            "sources_detail": {"primary": [], "related": []},
        }
        return state

    ql = question.lower()

    # -----------------------------
    # POLICY = source of truth
    # -----------------------------
    if any(p in ql for p in ["what roles are available", "available roles", "list roles", "roles available"]):
        roles = list_available_roles()
        state["chat"] = {
            "enabled": True,
            "question": question,
            "answer": "Available employee roles (from access policy):\n- " + "\n- ".join(roles) if roles else
                      "No roles found. Check config/access_policies.yml",
            "sources": ["config/access_policies.yml"],
            "sources_detail": {"primary": ["config/access_policies.yml"], "related": []},
        }
        return state

    if any(p in ql for p in ["what access is required", "required access", "what systems do i need", "what permissions"]):
        # Try to extract role from question first
        role_in_q = _extract_role_from_question(question)
        role = role_in_q or _normalize_role(state_role)

        systems = systems_for_role(role)
        if systems:
            state["chat"] = {
                "enabled": True,
                "question": question,
                "answer": f"Access for role **{role}** (from access policy):\n- " + "\n- ".join(systems),
                "sources": ["config/access_policies.yml"],
                "sources_detail": {"primary": ["config/access_policies.yml"], "related": []},
            }
            return state
        # If policy does not contain role, we continue to RAG answer (best effort)

    # -----------------------------
    # RAG knowledge answer
    # -----------------------------
    context_text, sources_detail = _get_rag_from_state(state)

    # If onboarding_agent didn't populate context, retrieve now
    if not context_text.strip():
        context_text, sources_detail = _fallback_retrieve(question, k=6)

    primary = sources_detail.get("primary", []) or []
    related = sources_detail.get("related", []) or []
    flat_sources = list(dict.fromkeys(primary + related))

    # If still empty context, give a basic helpful answer
    if not context_text.strip():
        fallback = (
            "I don’t have enough internal context loaded to answer that precisely.\n\n"
            "Try:\n"
            "- Ask HR where the onboarding guide lives (often Confluence / HR portal)\n"
            "- If you have Confluence: search for “Employee Onboarding (Day 0–30)”\n"
            "- Or run `python -m rag.ingest` to rebuild the index after updating docs\n"
        )
        state["chat"] = {
            "enabled": True,
            "question": question,
            "answer": fallback,
            "sources": flat_sources,
            "sources_detail": {"primary": primary, "related": related},
        }
        return state

    # Gemini call
    try:
        if not GOOGLE_API_KEY:
            raise RuntimeError("Missing GOOGLE_API_KEY (or GEMINI_API_KEY). Set it in .env")

        llm = ChatGoogleGenerativeAI(
            model=GEMINI_CHAT_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=float(os.getenv("CHAT_TEMPERATURE", "0.2")),
        )

        sys = SystemMessage(
            content=(
                "You are an internal onboarding/offboarding assistant.\n"
                "Use the provided internal context as your primary source.\n"
                "If the answer exists in the context, answer confidently and cite the relevant source name(s).\n"
                "If not present, say what is missing and suggest where to find it.\n"
                "Keep answers concise and practical."
            )
        )

        user = HumanMessage(
            content=(
                f"Employee: {name}\n"
                f"Role: {state_role}\n\n"
                f"Question: {question}\n\n"
                f"Internal context:\n{context_text}\n"
            )
        )

        resp = llm.invoke([sys, user])
        answer = getattr(resp, "content", str(resp)).strip()

        state["chat"] = {
            "enabled": True,
            "question": question,
            "answer": answer if answer else "(no answer returned)",
            "sources": flat_sources,
            "sources_detail": {"primary": primary, "related": related},
        }

    except Exception as e:
        state["chat"] = {
            "enabled": True,
            "question": question,
            "answer": "(chat error)",
            "error": str(e),
            "sources": flat_sources,
            "sources_detail": {"primary": primary, "related": related},
        }

    return state
