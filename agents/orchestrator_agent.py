from langgraph.graph import StateGraph, END

from agents.onboarding_agent import onboarding_agent
from agents.provisioning_agent import provisioning_agent
from agents.kt_agent import kt_agent
from agents.chat_agent import chat_agent
from agents.report_agent import report_agent

def build_full_graph():
    # ✅ Use a plain dict state so no keys get filtered/dropped
    graph_builder = StateGraph(dict)

    graph_builder.add_node("start", lambda s: s)
    graph_builder.add_node("onboarding_agent", onboarding_agent)
    graph_builder.add_node("provisioning_agent", provisioning_agent)
    graph_builder.add_node("kt_agent", kt_agent)
    graph_builder.add_node("chat_agent", chat_agent)
    graph_builder.add_node("report_agent", report_agent)

    graph_builder.set_entry_point("start")

    graph_builder.add_edge("start", "onboarding_agent")
    graph_builder.add_edge("onboarding_agent", "provisioning_agent")
    graph_builder.add_edge("provisioning_agent", "kt_agent")
    graph_builder.add_edge("kt_agent", "chat_agent")
    graph_builder.add_edge("chat_agent", "report_agent")
    graph_builder.add_edge("report_agent", END)

    return graph_builder.compile()
