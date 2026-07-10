"""
Graph orchestration module for the IncidentIQ Agent.
Compiles and exports the LangGraph workflow combining planning, retrieving, verification, replanning, and synthesis nodes.
"""

import time
import logging
from typing import Optional, Dict, Any, List

from langgraph.graph import StateGraph, END
from agent.state import IncidentState, new_incident_state
from agent.anonymizer import anonymize
from agent.planner import generate_plan
from agent.retriever import retrieve
from agent.call_graph_node import analyze_call_graph
from agent.verifier import verify
from agent.replanner import replan
from agent.synthesizer import synthesize

logger = logging.getLogger(__name__)


def anonymize_node(state: IncidentState) -> IncidentState:
    """
    StateGraph wrapper node for named-entity anonymization.
    """
    start_time = time.time()
    
    description = state.get("incident_description", "")
    anon, entity_map = anonymize(description)
    
    state["anonymized_query"] = anon
    state["entity_map"] = entity_map
    
    state["investigation_steps"].append({
        "step": "Anonymization",
        "detail": f"Anonymized private fields. Anonymized query: '{anon}'",
        "time": round(time.time() - start_time, 3)
    })
    return state


def planning_node(state: IncidentState) -> IncidentState:
    """
    StateGraph wrapper node for SRE plan generation.
    """
    start_time = time.time()
    
    query = state.get("anonymized_query", "")
    plan = generate_plan(query)
    
    state["plan"] = plan
    
    state["investigation_steps"].append({
        "step": "Planning",
        "detail": f"Formulated SRE plan with {len(plan)} sequential steps.",
        "time": round(time.time() - start_time, 3)
    })
    return state


def route_after_verification(state: IncidentState) -> str:
    """
    Conditional router. Decides whether to replan or proceed to synthesis.
    """
    is_grounded = state.get("is_grounded", False)
    replan_count = state.get("replan_count", 0)
    
    if is_grounded:
        logger.info("Verification passed. Grounded. Proceeding to synthesis.")
        return "synthesize"
        
    if replan_count < 3:
        logger.info(f"Verification failed. Replan count: {replan_count} < 3. Routing to replan.")
        return "replan"
        
    logger.warning(f"Verification failed, but replan count limit reached ({replan_count} >= 3). Routing to synthesize.")
    return "synthesize"


# Build the state graph workflow
workflow = StateGraph(IncidentState)

# Add processing nodes
workflow.add_node("anonymize", anonymize_node)
workflow.add_node("plan", planning_node)
workflow.add_node("retrieve", retrieve)
workflow.add_node("call_graph_analysis", analyze_call_graph)
workflow.add_node("verify", verify)
workflow.add_node("replan", replan)
workflow.add_node("synthesize", synthesize)

# Configure flow links
workflow.set_entry_point("anonymize")
workflow.add_edge("anonymize", "plan")
workflow.add_edge("plan", "retrieve")
workflow.add_edge("retrieve", "call_graph_analysis")
workflow.add_edge("call_graph_analysis", "verify")

# Conditional verification outcome
workflow.add_conditional_edges(
    "verify",
    route_after_verification,
    {
        "replan": "replan",
        "synthesize": "synthesize"
    }
)

# Replan loop-back to retrieve
workflow.add_edge("replan", "retrieve")

# End of graph from synthesis
workflow.add_edge("synthesize", END)

# Compile the workflow
app = workflow.compile()


def run_investigation(incident_description: str, error_logs: Optional[str] = None) -> IncidentState:
    """
    Entrypoint function. Orchestrates SRE investigation from description to markdown final report.

    Args:
        incident_description (str): Description of the incident.
        error_logs (Optional[str]): Error logs or stack traces, if any.

    Returns:
        IncidentState: The final SRE state after graph execution.
    """
    initial_state = new_incident_state(incident_description, error_logs)
    
    # Run compiled LangGraph SRE state machine
    final_state = app.invoke(initial_state)
    return final_state
