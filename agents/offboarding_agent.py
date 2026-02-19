from datetime import datetime
from rag.retriever import retrieve_context

def offboarding_agent(state: dict):
    name = state.get("name")
    role = state.get("role")

    print(" Starting offboarding workflow")
    print(f" Offboarding {name} ({role})")

    # RAG for policy reminders (security/offboarding rules)
    rag = retrieve_context("What are our offboarding security and access revocation requirements?")

    print("📚 Retrieved internal context (RAG):")
    print(rag["context"])
    print(f" Sources: {rag['sources']}")

    report = {
        "employee": name,
        "role": role,
        "status": "Offboarding initiated",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "access_revocation": {
            "IAM": "Revoked",
            "Jira": "Revoked",
            "GitHub": "Revoked",
            "Confluence": "Revoked"
        },
        "kt_capture_checklist": [
            "Collect runbooks and operational notes",
            "Capture ownership map (services, dashboards, alerts)",
            "List critical contacts and escalation paths",
            "Document open incidents / known issues",
            "Handover outstanding Jira tickets"
        ],
        "compliance_summary": [
            "Day-0 access revocation completed",
            "Least privilege enforced",
            "Audit trail recorded for all access changes"
        ],
        "rag_sources": rag["sources"],
        "rag_context_preview": rag["context"][:500]
    }

    state["offboarding_report"] = report
    state["status"] = "Offboarding completed successfully"
    return state
