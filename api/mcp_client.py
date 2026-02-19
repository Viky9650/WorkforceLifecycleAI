import os
import requests
from typing import Any, Dict, Optional

MCP_BASE_URL = os.getenv("MCP_BASE_URL", "http://127.0.0.1:8001")

def mcp_post(path: str, payload: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
    url = f"{MCP_BASE_URL}{path}"
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()

def notify_onboarding(employee: str, role: str, audit_id: Optional[str] = None, email: Optional[str] = None) -> Dict[str, Any]:
    return mcp_post(
        "/tools/notify/onboarding",
        {"employee": employee, "role": role, "audit_id": audit_id, "email": email},
    )

def notify_offboarding(employee: str, role: str, audit_id: Optional[str] = None) -> Dict[str, Any]:
    return mcp_post(
        "/tools/notify/offboarding",
        {"employee": employee, "role": role, "audit_id": audit_id},
    )
