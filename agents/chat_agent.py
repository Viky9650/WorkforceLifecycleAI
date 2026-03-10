"""
Chat Agent (Gemini + RAG + Policy + DB tools)

- Policy questions -> config/access_policies.yml
- Knowledge questions -> RAG context
- Employee queries -> Gemini calls safe DB tools
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import yaml
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from db.session import SessionLocal
from db.crud import (
    list_active_employees_tool,
    list_inactive_employees_tool,
    get_employee_access_tool,
    get_employee_status_tool,
)

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
POLICY_PATH = os.getenv(
    "ACCESS_POLICY_PATH",
    str(BASE_DIR / "config" / "access_policies.yml"),
)

GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


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
    except Exception as e:
        print(f"❌ Failed to load access policies: {e}")
        return {}


def list_available_roles() -> List[str]:
    pol = _load_policies()
    roles = [k for k in pol.keys() if isinstance(k, str)]
    return sorted(roles)


def _normalize_role(role: str) -> str:
    role = (role or "").strip()
    if not role:
        return ""
    return ROLE_ALIASES.get(role.lower(), role)


def systems_for_role(role: str) -> List[str]:
    pol = _load_policies()
    role = _normalize_role(role)
    role_obj = pol.get(role, {})
    if isinstance(role_obj, dict):
        systems = role_obj.get("systems", [])
        if isinstance(systems, list):
            return [str(s) for s in systems]
    return []


def _extract_role_from_question(question: str) -> Optional[str]:
    question = question or ""
    ql = question.lower()

    for key, canonical in ROLE_ALIASES.items():
        if re.search(rf"\b{re.escape(key)}\b", ql):
            return canonical

    match = re.search(r"for\s+([A-Za-z ]+)", question)
    if match:
        candidate = match.group(1).strip()
        policies = _load_policies()
        if candidate in policies:
            return candidate
        return _normalize_role(candidate)

    return None


def _get_rag_from_state(state: Dict[str, Any]) -> Tuple[str, Dict[str, List[str]]]:
    context = state.get("rag_context_preview") or ""
    sources = state.get("rag_sources") or {}

    if not isinstance(sources, dict):
        sources = {}

    primary = sources.get("primary") or sources.get("primary_sources") or []
    related = sources.get("related") or sources.get("related_sources") or []

    if not isinstance(primary, list):
        primary = []
    if not isinstance(related, list):
        related = []

    return str(context), {"primary": list(primary), "related": list(related)}


def _fallback_retrieve(question: str, k: int = 6) -> Tuple[str, Dict[str, List[str]]]:
    from rag.retriever import retrieve_context

    out = retrieve_context(question, k=k)

    if not isinstance(out, dict):
        return "", {"primary": [], "related": []}

    context = str(out.get("context", "") or "")
    primary = out.get("primary_sources", []) or []
    related = out.get("related_sources", []) or []

    if not isinstance(primary, list):
        primary = []
    if not isinstance(related, list):
        related = []

    return context, {"primary": list(primary), "related": list(related)}


def _message_to_text(msg: Any) -> str:
    """
    Gemini/LangChain may return content as:
    - str
    - list[str | dict | content parts]
    This helper normalizes everything into plain text safely.
    """
    content = getattr(msg, "content", "")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
            else:
                text = getattr(item, "text", None)
                if text:
                    parts.append(str(text))
                else:
                    parts.append(str(item))
        return "\n".join(p for p in parts if p).strip()

    return str(content).strip()


@tool
def list_active_employees() -> str:
    """List all active employees from the employee database."""
    db = SessionLocal()
    try:
        rows = list_active_employees_tool(db)
        return json.dumps(rows, indent=2)
    finally:
        db.close()


@tool
def list_inactive_employees() -> str:
    """List all inactive or offboarded employees from the employee database."""
    db = SessionLocal()
    try:
        rows = list_inactive_employees_tool(db)
        return json.dumps(rows, indent=2)
    finally:
        db.close()


@tool
def get_employee_access(employee_name: str) -> str:
    """Get system access details for a single employee by exact or close name."""
    db = SessionLocal()
    try:
        row = get_employee_access_tool(db, employee_name)
        return json.dumps(row, indent=2)
    finally:
        db.close()


@tool
def get_employee_status(employee_name: str) -> str:
    """Get employment status, lifecycle status, role, and manager for a single employee."""
    db = SessionLocal()
    try:
        row = get_employee_status_tool(db, employee_name)
        return json.dumps(row, indent=2)
    finally:
        db.close()


TOOLS = [
    list_active_employees,
    list_inactive_employees,
    get_employee_access,
    get_employee_status,
]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}


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
    # deterministic policy answers
    # -----------------------------
    if any(
        p in ql
        for p in [
            "what roles are available",
            "available roles",
            "list roles",
            "roles available",
        ]
    ):
        roles = list_available_roles()
        state["chat"] = {
            "enabled": True,
            "question": question,
            "answer": (
                "Available employee roles (from access policy):\n- " + "\n- ".join(roles)
                if roles
                else "No roles found. Check config/access_policies.yml"
            ),
            "sources": ["config/access_policies.yml"],
            "sources_detail": {"primary": ["config/access_policies.yml"], "related": []},
        }
        return state

    if any(
        p in ql
        for p in [
            "what access is required",
            "required access",
            "what systems do i need",
            "what permissions",
        ]
    ):
        role_in_question = _extract_role_from_question(question)
        resolved_role = role_in_question or _normalize_role(state_role)

        systems = systems_for_role(resolved_role)
        if systems:
            state["chat"] = {
                "enabled": True,
                "question": question,
                "answer": f"Access for role **{resolved_role}** (from access policy):\n- " + "\n- ".join(systems),
                "sources": ["config/access_policies.yml"],
                "sources_detail": {"primary": ["config/access_policies.yml"], "related": []},
            }
            return state

    # -----------------------------
    # RAG context
    # -----------------------------
    context_text, sources_detail = _get_rag_from_state(state)
    if not context_text.strip():
        context_text, sources_detail = _fallback_retrieve(question, k=6)

    primary = sources_detail.get("primary", []) or []
    related = sources_detail.get("related", []) or []
    flat_sources = list(dict.fromkeys(primary + related))

    max_context_chars = int(os.getenv("MAX_CONTEXT_CHARS", "2500"))
    context_text = context_text[:max_context_chars]

    try:
        if not GOOGLE_API_KEY:
            raise RuntimeError("Missing GOOGLE_API_KEY (or GEMINI_API_KEY). Set it in .env")
        if not GEMINI_CHAT_MODEL:
            raise RuntimeError("Missing GEMINI_CHAT_MODEL. Set it in .env")

        print(f"🤖 Chat Agent: calling Gemini model={GEMINI_CHAT_MODEL}")

        llm = ChatGoogleGenerativeAI(
            model=GEMINI_CHAT_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=float(os.getenv("CHAT_TEMPERATURE", "0.2")),
        )

        llm_with_tools = llm.bind_tools(TOOLS)

        messages = [
            SystemMessage(
                content=(
                    "You are an internal onboarding/offboarding assistant.\n"
                    "Use tools for employee database questions.\n"
                    "Use the provided internal document context for knowledge questions.\n"
                    "When tool results are available, treat them as the source of truth.\n"
                    "Do not invent employees, statuses, or access that are not present in tool results.\n"
                    "If the answer exists in the internal document context, answer from it clearly.\n"
                    "Keep answers concise, practical, and grounded."
                )
            ),
            HumanMessage(
                content=(
                    f"Employee: {name}\n"
                    f"Role: {state_role}\n\n"
                    f"Question: {question}\n\n"
                    f"Internal document context:\n{context_text}\n"
                )
            ),
        ]

        first = llm_with_tools.invoke(messages)
        messages.append(first)

        tool_sources: List[str] = []

        if getattr(first, "tool_calls", None):
            for tc in first.tool_calls:
                tool_name = tc["name"]
                tool_args = tc.get("args", {}) or {}
                tool_fn = TOOLS_BY_NAME[tool_name]
                tool_result = tool_fn.invoke(tool_args)
                tool_sources.append("employees_db")

                messages.append(
                    ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tc["id"],
                    )
                )

            final_resp = llm_with_tools.invoke(messages)
            answer = _message_to_text(final_resp)
            final_sources = list(dict.fromkeys(flat_sources + tool_sources))
        else:
            answer = _message_to_text(first)
            final_sources = flat_sources

        state["chat"] = {
            "enabled": True,
            "question": question,
            "answer": answer if answer else "(no answer returned)",
            "sources": final_sources,
            "sources_detail": {"primary": primary, "related": related},
        }

    except Exception as e:
        print(f"❌ Chat Agent Error: {e}")
        state["chat"] = {
            "enabled": True,
            "question": question,
            "answer": f"(chat error) {str(e)}",
            "error": str(e),
            "sources": flat_sources,
            "sources_detail": {"primary": primary, "related": related},
        }

    return state