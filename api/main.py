from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Annotated
from pathlib import Path
import json

from agents.orchestrator_agent import build_full_graph
from api.storage_routes import router as storage_router

from db.session import SessionLocal, engine
from db.crud import (
    init_db,
    persist_workflow_result,
    get_dashboard,
    get_user_by_email,
    get_distinct_roles,
)

app = FastAPI(title="OnboardAI API", version="1.0")

# --- CORS (frontend) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Storage routes (/runs etc) ---
app.include_router(storage_router)

graph = build_full_graph()

# --- Initialize DB ---
init_db(engine)


# -----------------------
# Request models
# -----------------------
class ChatRequest(BaseModel):
    name: str = "User"
    email: str = "user@company.com"
    manager_email: str = "manager@company.com"
    role: str = "Employee"
    question: str


class OnboardRequest(BaseModel):
    name: str
    email: str = "user@company.com"
    manager_email: str = "manager@company.com"
    role: str
    question: Optional[str] = None


class OffboardRequest(BaseModel):
    name: str
    email: str = "user@company.com"
    manager_email: str = "manager@company.com"
    role: str
    question: Optional[str] = None
    kt_notes: Optional[str] = None


# -----------------------
# Auth helpers
# -----------------------
def require_hr_or_admin(user_email: str):
    db = SessionLocal()
    try:
        user = get_user_by_email(db, user_email)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        if user.role not in ["admin", "hr"]:
            raise HTTPException(status_code=403, detail="Only HR or Admin can perform this action")
        return user
    finally:
        db.close()


# -----------------------
# Current user
# -----------------------
@app.get("/me")
def me(x_user_email: Annotated[str, Header(...)]):
    db = SessionLocal()
    try:
        user = get_user_by_email(db, x_user_email)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        return {
            "name": user.name,
            "email": user.email,
            "role": user.role,
        }
    finally:
        db.close()


# -----------------------
# Employee dashboard
# -----------------------
@app.get("/employees/dashboard")
def employees_dashboard(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
    search: str | None = None,
    status: str | None = None,
    role: str | None = None,
):
    db = SessionLocal()
    try:
        return get_dashboard(
            db,
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            role=role,
        )
    finally:
        db.close()


@app.get("/employees/roles")
def employee_roles():
    db = SessionLocal()
    try:
        return {"roles": get_distinct_roles(db)}
    finally:
        db.close()


# -----------------------
# Chat-only endpoint
# -----------------------
@app.post("/chat")
def chat(req: ChatRequest) -> Dict[str, Any]:
    """
    Chat-only: RAG + Chat Agent.
    No provisioning, no offboarding actions.
    """
    state: Dict[str, Any] = {
        "name": req.name,
        "email": req.email,
        "manager_email": req.manager_email,
        "role": req.role,
        "question": req.question,
        "action": "chat",
    }

    trace: List[Dict[str, Any]] = []

    # 1) RAG grounding
    try:
        from agents.onboarding_agent import onboarding_agent
        state = onboarding_agent(state)
        trace.append({
            "agent": "Onboarding Agent",
            "status": "ok",
            "detail": "RAG context retrieved",
        })
    except Exception as e:
        print(f"❌ Onboarding Agent Error: {e}")
        trace.append({
            "agent": "Onboarding Agent",
            "status": "error",
            "detail": str(e),
        })

    # 2) Chat answer
    try:
        from agents.chat_agent import chat_agent
        state = chat_agent(state)

        chat_obj = state.get("chat", {}) or {}
        if chat_obj.get("error"):
            trace.append({
                "agent": "Chat Agent",
                "status": "error",
                "detail": chat_obj.get("error"),
            })
        else:
            trace.append({
                "agent": "Chat Agent",
                "status": "ok",
                "detail": "Answer generated",
            })

    except Exception as e:
        print(f"❌ /chat endpoint error while calling chat_agent: {e}")
        trace.append({
            "agent": "Chat Agent",
            "status": "error",
            "detail": str(e),
        })
        state["chat"] = {
            "enabled": True,
            "question": req.question,
            "answer": f"(chat error) {str(e)}",
            "error": str(e),
            "sources": state.get("rag_sources", []),
        }

    return {
        "mode": "chat",
        "name": req.name,
        "email": req.email,
        "manager_email": req.manager_email,
        "role": req.role,
        "question": req.question,
        "rag_context_preview": state.get("rag_context_preview"),
        "rag_sources": state.get("rag_sources"),
        "chat": state.get("chat"),
        "trace": trace,
    }


# -----------------------
# Lifecycle endpoints
# -----------------------
@app.post("/onboard")
def onboard(req: OnboardRequest, x_user_email: Annotated[str, Header(...)]):
    current_user = require_hr_or_admin(x_user_email)

    result = graph.invoke(
        {
            "name": req.name,
            "email": req.email,
            "manager_email": req.manager_email,
            "role": req.role,
            "action": "onboard",
            "question": req.question,
            "status": "",
        }
    )

    db = SessionLocal()
    try:
        persist_workflow_result(
            db,
            result=result,
            initiated_by=current_user.email,
            initiator_role=current_user.role,
        )
    finally:
        db.close()

    return result


@app.post("/offboard")
def offboard(req: OffboardRequest, x_user_email: Annotated[str, Header(...)]):
    current_user = require_hr_or_admin(x_user_email)

    result = graph.invoke(
        {
            "name": req.name,
            "email": req.email,
            "manager_email": req.manager_email,
            "role": req.role,
            "action": "offboard",
            "question": req.question,
            "kt_notes": req.kt_notes,
            "status": "",
        }
    )

    db = SessionLocal()
    try:
        persist_workflow_result(
            db,
            result=result,
            initiated_by=current_user.email,
            initiator_role=current_user.role,
        )
    finally:
        db.close()

    return result


# -----------------------
# Run loader endpoint
# -----------------------
RUNS_DIR = Path("store/runs").resolve()


@app.get(
    "/run",
    responses={
        400: {"description": "Invalid path"},
        404: {"description": "Run not found"},
    },
)
def get_run(path: Annotated[str, Query(description="Run filename or path returned by /runs")]):
    requested = Path(path)

    if requested.parent == Path("."):
        requested = (RUNS_DIR / requested.name).resolve()
    else:
        if not requested.is_absolute():
            requested = (Path.cwd() / requested).resolve()
        else:
            requested = requested.resolve()

    if RUNS_DIR not in requested.parents:
        raise HTTPException(status_code=400, detail="Invalid path")

    if not requested.exists() or requested.suffix.lower() != ".json":
        raise HTTPException(status_code=404, detail="Run not found")

    return json.loads(requested.read_text(encoding="utf-8"))