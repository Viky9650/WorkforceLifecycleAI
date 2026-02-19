from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI(title="OnboardAI MCP Server", version="1.4")


# -----------------------------
# Helpers
# -----------------------------
def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit_id() -> str:
    return "AUD-" + uuid.uuid4().hex[:10].upper()


def _msg_id(prefix: str) -> str:
    return f"{prefix}-" + uuid.uuid4().hex[:10].upper()


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v is not None and v != "" else default


# -----------------------------
# Models
# -----------------------------
class ProvisionRequest(BaseModel):
    user: str
    role: str
    payload: Dict[str, Any] = {}


class NotifyRequest(BaseModel):
    # Email fields
    to: Optional[List[str]] = None
    subject: Optional[str] = None
    body: Optional[str] = None

    # Slack fields
    channel: Optional[str] = None
    text: Optional[str] = None

    # Meta (audit, employee, role, etc)
    meta: Dict[str, Any] = {}


# -----------------------------
# Health + audit
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": _utcnow()}


@app.post("/audit/new")
def new_audit(req: ProvisionRequest):
    return {"audit_id": _audit_id(), "timestamp": _utcnow(), "user": req.user, "role": req.role}


# -----------------------------
# Core systems (mock)
# -----------------------------
@app.post("/iam/provision")
def iam_provision(req: ProvisionRequest):
    return {"system": "IAM", "action": "provision", "user": req.user, "timestamp": _utcnow(), "result": "Granted", "details": req.payload}


@app.post("/iam/revoke")
def iam_revoke(req: ProvisionRequest):
    return {"system": "IAM", "action": "revoke", "user": req.user, "timestamp": _utcnow(), "result": "Revoked", "details": req.payload}


@app.post("/jira/provision")
def jira_provision(req: ProvisionRequest):
    return {"system": "Jira", "action": "provision", "user": req.user, "timestamp": _utcnow(), "result": "Granted", "details": req.payload}


@app.post("/jira/revoke")
def jira_revoke(req: ProvisionRequest):
    return {"system": "Jira", "action": "revoke", "user": req.user, "timestamp": _utcnow(), "result": "Revoked", "details": req.payload}


@app.post("/confluence/provision")
def confluence_provision(req: ProvisionRequest):
    return {"system": "Confluence", "action": "provision", "user": req.user, "timestamp": _utcnow(), "result": "Granted", "details": req.payload}


@app.post("/confluence/revoke")
def confluence_revoke(req: ProvisionRequest):
    return {"system": "Confluence", "action": "revoke", "user": req.user, "timestamp": _utcnow(), "result": "Revoked", "details": req.payload}


@app.post("/devops_deploy_app/provision")
def devops_deploy_app_provision(req: ProvisionRequest):
    return {"system": "Devops Deploy App", "action": "provision", "user": req.user, "timestamp": _utcnow(), "result": "Granted", "details": req.payload}


@app.post("/devops_deploy_app/revoke")
def devops_deploy_app_revoke(req: ProvisionRequest):
    return {"system": "Devops Deploy App", "action": "revoke", "user": req.user, "timestamp": _utcnow(), "result": "Revoked", "details": req.payload}


@app.post("/service_now/provision")
def service_now_provision(req: ProvisionRequest):
    return {"system": "Service Now", "action": "provision", "user": req.user, "timestamp": _utcnow(), "result": "Granted", "details": req.payload}


@app.post("/service_now/revoke")
def service_now_revoke(req: ProvisionRequest):
    return {"system": "Service Now", "action": "revoke", "user": req.user, "timestamp": _utcnow(), "result": "Revoked", "details": req.payload}


@app.post("/outlook/provision")
def outlook_provision(req: ProvisionRequest):
    return {"system": "Outlook", "action": "provision", "user": req.user, "timestamp": _utcnow(), "result": "Granted", "details": req.payload}


@app.post("/outlook/revoke")
def outlook_revoke(req: ProvisionRequest):
    return {"system": "Outlook", "action": "revoke", "user": req.user, "timestamp": _utcnow(), "result": "Revoked", "details": req.payload}


@app.post("/teams/provision")
def teams_provision(req: ProvisionRequest):
    return {"system": "Teams", "action": "provision", "user": req.user, "timestamp": _utcnow(), "result": "Granted", "details": req.payload}


@app.post("/teams/revoke")
def teams_revoke(req: ProvisionRequest):
    return {"system": "Teams", "action": "revoke", "user": req.user, "timestamp": _utcnow(), "result": "Revoked", "details": req.payload}


# -----------------------------
# Notifications (mock Slack + Email)
# -----------------------------
@app.post("/tools/notify/onboarding")
def notify_onboarding(req: NotifyRequest):
    email = {
        "provider": "email",
        "mode": "mock",
        "status": "sent",
        "message_id": _msg_id("EML"),
        "timestamp": _utcnow(),
        "to": req.to or ["employee@company.com", "hr@company.com", "it-support@company.com"],
        "subject": req.subject or "Welcome! Your onboarding is complete ✅",
        "body_preview": (req.body[:160] + "…") if req.body else "Welcome aboard! Your access has been provisioned.",
        "meta": req.meta,
    }
    slack = {
        "provider": "slack",
        "mode": "mock",
        "status": "sent",
        "message_id": _msg_id("SLK"),
        "timestamp": _utcnow(),
        "channel": req.channel or "#hr-onboarding",
        "text_preview": (req.text[:160] + "…") if req.text else "Onboarding completed ✅ (audit attached)",
        "meta": req.meta,
    }
    return {"email": email, "slack": slack}


@app.post("/tools/notify/offboarding")
def notify_offboarding(req: NotifyRequest):
    email = {
        "provider": "email",
        "mode": "mock",
        "status": "sent",
        "message_id": _msg_id("EML"),
        "timestamp": _utcnow(),
        "to": req.to or ["hr@company.com", "it-support@company.com", "security@company.com"],
        "subject": req.subject or "Offboarding completed ✅ (Access revoked)",
        "body_preview": (req.body[:160] + "…") if req.body else "Offboarding completed. Access revoked. KT captured.",
        "meta": req.meta,
    }
    slack = {
        "provider": "slack",
        "mode": "mock",
        "status": "sent",
        "message_id": _msg_id("SLK"),
        "timestamp": _utcnow(),
        "channel": req.channel or "#security-audit",
        "text_preview": (req.text[:160] + "…") if req.text else "Offboarding completed ✅ Access revoked + audit logged.",
        "meta": req.meta,
    }
    return {"email": email, "slack": slack}


# -----------------------------
# GitHub (REAL) – Enterprise API
# -----------------------------
GITHUB_API_BASE = _env("GITHUB_API_BASE", "https://api.github.ibm.com")
GITHUB_ORG = _env("GITHUB_ORG")
GITHUB_TOKEN = _env("GITHUB_TOKEN") or _env("GITHUB_PAT")


@app.get("/debug/github")
def debug_github():
    return {
        "api_base": GITHUB_API_BASE,
        "org": GITHUB_ORG,
        "has_token": bool(GITHUB_TOKEN),
    }


def _gh_headers() -> Dict[str, str]:
    if not GITHUB_TOKEN:
        raise HTTPException(status_code=500, detail="Missing GITHUB_TOKEN (or GITHUB_PAT) in environment")
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def _gh_org(req: ProvisionRequest) -> str:
    # allow payload override
    org = (req.payload or {}).get("org") or GITHUB_ORG
    if not org:
        raise HTTPException(status_code=400, detail="Missing GITHUB_ORG (or payload.org)")
    return str(org)


def _gh_pending(detail: Dict[str, Any]) -> Dict[str, Any]:
    # Standard “pending” response your access_agent can treat as OK
    return {
        "system": "GitHub",
        "result": "Pending (Admin approval required)",
        "details": detail,
        "timestamp": _utcnow(),
    }


def _gh_request(method: str, url: str, json_body: Optional[dict] = None) -> requests.Response:
    return requests.request(
        method=method.upper(),
        url=url,
        headers=_gh_headers(),
        json=json_body,
        timeout=15,
    )


@app.post("/github/provision")
def github_provision(req: ProvisionRequest):
    """
    Provision GitHub access for a user.
    Supports:
      - org membership (requires admin privileges / PAT scopes)
      - optional team membership: payload.team_slug
      - optional repo creation: payload.create_repo (bool) + payload.repo_name
    If GitHub returns 403/404 due to permissions, we return "Pending".
    """
    org = _gh_org(req)
    username = req.user.strip()

    team_slug = (req.payload or {}).get("team_slug")
    create_repo = bool((req.payload or {}).get("create_repo", False))
    repo_name = (req.payload or {}).get("repo_name")

    # 1) Ensure org membership
    membership_url = f"{GITHUB_API_BASE}/orgs/{org}/memberships/{username}"
    r = _gh_request("PUT", membership_url, json_body={"role": "member"})
    if r.status_code in (401,):
        raise HTTPException(status_code=401, detail={"github_path": f"/orgs/{org}/memberships/{username}", "status": r.status_code, "body": r.json()})
    if r.status_code in (403, 404):
        # 403 often means PAT lacks org admin permission
        return _gh_pending({"github_path": f"/orgs/{org}/memberships/{username}", "status": r.status_code, "body": r.json()})
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail={"github_path": f"/orgs/{org}/memberships/{username}", "status": r.status_code, "body": r.json()})

    out: Dict[str, Any] = {
        "system": "GitHub",
        "action": "provision",
        "user": username,
        "timestamp": _utcnow(),
        "result": "Granted",
        "details": {"org": org, "membership": "member"},
    }

    # 2) Optional: add to team
    if team_slug:
        team_url = f"{GITHUB_API_BASE}/orgs/{org}/teams/{team_slug}/memberships/{username}"
        tr = _gh_request("PUT", team_url, json_body={"role": "member"})
        if tr.status_code in (403, 404):
            # membership worked but team add might be blocked
            out["result"] = "Pending (Admin approval required)"
            out["details"]["team"] = {"team_slug": team_slug, "status": tr.status_code, "body": tr.json()}
            return out
        if tr.status_code >= 400:
            out["result"] = "Pending (Admin approval required)"
            out["details"]["team"] = {"team_slug": team_slug, "status": tr.status_code, "body": tr.json()}
            return out
        out["details"]["team"] = {"team_slug": team_slug, "added": True}

    # 3) Optional: create repo under org
    if create_repo:
        if not repo_name:
            out["details"]["repo"] = {"created": False, "reason": "payload.repo_name missing"}
        else:
            repo_url = f"{GITHUB_API_BASE}/orgs/{org}/repos"
            rr = _gh_request("POST", repo_url, json_body={"name": repo_name, "private": True})
            if rr.status_code in (403, 404):
                out["result"] = "Pending (Admin approval required)"
                out["details"]["repo"] = {"repo_name": repo_name, "status": rr.status_code, "body": rr.json()}
                return out
            if rr.status_code >= 400:
                out["result"] = "Pending (Admin approval required)"
                out["details"]["repo"] = {"repo_name": repo_name, "status": rr.status_code, "body": rr.json()}
                return out
            out["details"]["repo"] = {"repo_name": repo_name, "created": True}

    return out


@app.post("/github/revoke")
def github_revoke(req: ProvisionRequest):
    """
    Revoke GitHub access for a user from an org.
    If blocked by permissions -> Pending.
    """
    org = _gh_org(req)
    username = req.user.strip()

    # DELETE membership
    membership_url = f"{GITHUB_API_BASE}/orgs/{org}/memberships/{username}"
    r = _gh_request("DELETE", membership_url)

    if r.status_code in (401,):
        raise HTTPException(status_code=401, detail={"github_path": f"/orgs/{org}/memberships/{username}", "status": r.status_code, "body": r.text})
    if r.status_code in (403, 404):
        return _gh_pending({"github_path": f"/orgs/{org}/memberships/{username}", "status": r.status_code, "body": (r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text)})
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail={"github_path": f"/orgs/{org}/memberships/{username}", "status": r.status_code, "body": r.text})

    return {
        "system": "GitHub",
        "action": "revoke",
        "user": username,
        "timestamp": _utcnow(),
        "result": "Revoked",
        "details": {"org": org, "membership_removed": True, "meta": req.payload},
    }
