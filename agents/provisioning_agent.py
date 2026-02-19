# agents/access_agent.py
from __future__ import annotations

import os
import time
from typing import Any, Dict

import yaml
import httpx
from dotenv import load_dotenv

load_dotenv()

MCP_BASE = os.getenv("MCP_BASE_URL", "http://127.0.0.1:9001")
POLICY_PATH = os.getenv("ACCESS_POLICY_PATH", "config/access_policies.yml")

MAX_RETRIES = int(os.getenv("PROVISION_MAX_RETRIES", "3"))
RETRY_BACKOFF_SECONDS = float(os.getenv("PROVISION_RETRY_BACKOFF", "1.0"))

NOTIFY_ENABLED = os.getenv("NOTIFY_ENABLED", "true").lower() in ("1", "true", "yes")
NOTIFY_MAX_RETRIES = int(os.getenv("NOTIFY_MAX_RETRIES", "3"))
NOTIFY_BACKOFF_SECONDS = float(os.getenv("NOTIFY_RETRY_BACKOFF", "1.0"))

SYSTEM_ROUTE_MAP = {
    "IAM": "iam",
    "Jira": "jira",
    "GitHub": "github",
    "Confluence": "confluence",
    "Devops Deploy App": "devops_deploy_app",
    "Service Now": "service_now",
    "Outlook": "outlook",
    "Teams": "teams",
}

ROLE_ALIASES = {
    "Devops": "DevOps Engineer",
    "DevOps": "DevOps Engineer",
    "Infra": "Infrastructure Specialist",
    "Infrastructure": "Infrastructure Specialist",
}

def _normalize_key(s: str) -> str:
    return s.strip().lower().replace(" ", "_")

def _load_policy(role: str) -> dict:
    with open(POLICY_PATH, "r") as f:
        policies = yaml.safe_load(f) or {}
    if role not in policies:
        raise ValueError(f"Role '{role}' not found in {POLICY_PATH}")
    return policies[role]

def _post_with_retry(path: str, body: dict, *, max_retries: int = MAX_RETRIES, backoff: float = RETRY_BACKOFF_SECONDS) -> dict:
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            with httpx.Client(timeout=15.0) as client:
                r = client.post(f"{MCP_BASE}{path}", json=body)
                r.raise_for_status()
                return r.json()
        except Exception as e:
            last_err = str(e)
            if attempt < max_retries:
                time.sleep(backoff * attempt)
            else:
                return {"error": last_err}
    return {"error": last_err or "unknown"}

def _send_notifications(state: dict) -> dict:
    """
    Calls MCP notification tools and stores results under state["notifications"].
    Does NOT raise (never breaks onboarding/offboarding).
    """
    if not NOTIFY_ENABLED:
        state["notifications"] = {"disabled": True}
        return state

    action = (state.get("action") or "onboard").lower()
    name = state.get("name") or "User"
    role = state.get("role") or "Employee"

    # optional fields from API/UI
    email = state.get("email") or f"{name.lower()}@company.com"
    manager_email = state.get("manager_email") or "manager@company.com"

    audit_id = None
    if isinstance(state.get("access"), dict):
        audit_id = state["access"].get("audit_id")
    audit_id = audit_id or f"AUD-LOCAL-{int(time.time())}"

    notify_path = "/tools/notify/onboarding" if action != "offboard" else "/tools/notify/offboarding"

    body = {
        "user": name,
        "role": role,
        "payload": {
            "employee": name,
            "employee_email": email,
            "manager_email": manager_email,
            "role": role,
            "audit_id": audit_id,
            "action": action,
        },
    }

    resp = _post_with_retry(
        notify_path,
        body,
        max_retries=NOTIFY_MAX_RETRIES,
        backoff=NOTIFY_BACKOFF_SECONDS,
    )

    # Normalize output to what frontend expects
    notifications: Dict[str, Any] = {"slack": None, "email": None}

    if "error" in resp:
        state["notifications"] = {"error": resp["error"], "slack": None, "email": None}
        return state

    # If MCP returns combined {slack:{}, email:{}}
    if isinstance(resp, dict) and ("slack" in resp or "email" in resp):
        notifications["slack"] = resp.get("slack")
        notifications["email"] = resp.get("email")
        state["notifications"] = notifications
        return state

    # If MCP returns a single message
    provider = (resp.get("provider") or "").lower() if isinstance(resp, dict) else ""
    if provider == "slack":
        notifications["slack"] = resp
    elif provider == "email":
        notifications["email"] = resp
    else:
        notifications["email"] = resp  # fallback

    state["notifications"] = notifications
    return state

def provisioning_agent(state: dict):
    """
    Access/Provisioning Agent:
    - Reads role policies from config/access_policies.yml
    - Calls MCP per-system endpoints sequentially with retries
    - Produces consolidated access result + audit_id
    - ✅ Also triggers notifications (Slack/Email) via MCP and stores in state["notifications"]
    """
    name = state.get("name", "unknown")
    role = state.get("role", "unknown")
    role = ROLE_ALIASES.get(role, role)
    action = state.get("action", "onboard")  # onboard/offboard

    print("Access/Provisioning Agent: role policy + sequential provisioning")
    print(f" {name} | Role: {role} | Action: {action}")

    # Load role policy (source of truth)
    try:
        policy = _load_policy(role)
    except Exception as e:
        state["access"] = {"error": f"Policy load failed: {e}", "audit_id": None}
        # still try to notify (will show error in UI)
        state = _send_notifications(state)
        return state

    systems = policy.get("systems", ["IAM", "Jira", "GitHub", "Confluence"])

    # Create audit id
    audit_resp = _post_with_retry("/audit/new", {"user": name, "role": role, "payload": {}})
    audit_id = audit_resp.get("audit_id") or f"AUD-LOCAL-{int(time.time())}"

    def endpoint(system: str) -> str:
        key = SYSTEM_ROUTE_MAP.get(system) or _normalize_key(system)
        return f"/{key}/revoke" if action == "offboard" else f"/{key}/provision"

    results = {}
    steps = []

    for system in systems:
        policy_key = SYSTEM_ROUTE_MAP.get(system) or _normalize_key(system)
        payload = policy.get(policy_key, {}) or {}
        body = {"user": name, "role": role, "payload": payload}

        print(f"🔧 {system}: calling MCP {endpoint(system)}")
        resp = _post_with_retry(endpoint(system), body)

        if "error" in resp:
            results[system] = "Failed"
            steps.append({"system": system, "status": "Failed", "error": resp["error"]})
        else:
            results[system] = resp.get("result", "Unknown")
            steps.append({"system": system, "status": results[system], "details": resp.get("details", {})})

    all_ok = all(v in ("Granted", "Revoked") for v in results.values())

    state["access"] = {
        "action": "provision" if action != "offboard" else "revoke",
        "user": name,
        "role": role,
        "audit_id": audit_id,
        "systems": results,
        "steps": steps,
        "verified": all_ok,
    }

    print(f"Provisioning completed. verified={all_ok} audit_id={audit_id}")

    # ✅ Notifications (store result so UI can show it)
    state = _send_notifications(state)

        # ✅ Add notifications summary into audit/evidence
    try:
        n = state.get("notifications") or {}
        slack = n.get("slack") or {}
        email = n.get("email") or {}

        note = {
            "sent": bool(slack) or bool(email),
            "slack": {
                "status": slack.get("status"),
                "channel": slack.get("channel"),
                "message_id": slack.get("message_id"),
                "timestamp": slack.get("timestamp"),
            } if slack else None,
            "email": {
                "status": email.get("status"),
                "to": email.get("to"),
                "subject": email.get("subject"),
                "message_id": email.get("message_id"),
                "timestamp": email.get("timestamp"),
            } if email else None,
        }

        if isinstance(state.get("access"), dict):
            state["access"]["notifications"] = note
    except Exception:
        pass


    return state
