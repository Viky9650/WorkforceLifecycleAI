from datetime import datetime
from store.utils import save_kt
from rag.kt_index import add_kt_to_index

def kt_agent(state: dict):
    """
    Captures KT during offboarding and persists to store/kt/<name>_kt.json
    """
    action = state.get("action", "onboard")
    name = state.get("name", "unknown")

    if action != "offboard":
        state["kt"] = {"captured": False}
        return state

    print("📝 KT Agent: capturing knowledge transfer")

    kt_payload = {
        "captured": True,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "employee": name,
        "checklist": [
            "Runbooks and operational notes captured",
            "Dashboards/alerts ownership documented",
            "Escalation paths + contacts listed",
            "Open incidents and known issues documented",
            "Outstanding tickets handed over"
        ],
        # optional placeholder for actual notes
        "notes": state.get("kt_notes", "")
    }

    state["kt"] = kt_payload

    # ✅ Persist KT
    kt_path = save_kt(name, kt_payload)
    index_status = add_kt_to_index(kt_payload)
    state["kt"]["indexed_to_rag"] = index_status


    return state
