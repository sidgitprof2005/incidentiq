"""
Call graph analysis node for the IncidentIQ Agent SRE workflow.
"""

import os
import pickle
import time
import logging
from typing import Set
from agent.state import IncidentState

logger = logging.getLogger(__name__)


def analyze_call_graph(state: IncidentState) -> IncidentState:
    """
    Loads stores/call_graph.pkl, identifies the affected services/functions 
    mentioned in the retrieved code chunks, calls get_blast_radius() on them, 
    and populates state["call_graph_context"] and state["blast_radius"].

    Args:
        state (IncidentState): The current agent state.

    Returns:
        IncidentState: The updated agent state.
    """
    start_time = time.time()
    
    call_graph_path = os.path.join("stores", "call_graph.pkl")
    if not os.path.exists(call_graph_path):
        logger.warning("Call graph file not found at stores/call_graph.pkl. Skipping call graph analysis.")
        state["investigation_steps"].append({
            "step": "Call Graph Analysis",
            "detail": "Skipped: Call graph index stores/call_graph.pkl not found.",
            "time": round(time.time() - start_time, 3)
        })
        return state
        
    try:
        with open(call_graph_path, "rb") as f:
            G = pickle.load(f)
            
        # Discover functions present in the retrieved context
        functions_to_check: Set[str] = set()
        for item in state.get("retrieved_context", []):
            meta = item.get("metadata", {})
            doc_type = meta.get("type")
            if doc_type in ("method", "function", "class"):
                name = meta.get("name")
                class_name = meta.get("class_name")
                if name:
                    node_name = f"{class_name}.{name}" if class_name else name
                    if node_name in G:
                        functions_to_check.add(node_name)
                        
        blast_radius_set: Set[str] = set()
        call_graph_context_set: Set[str] = set()
        
        for func in functions_to_check:
            # Query blast radius from CallGraph
            radius = G.get_blast_radius(func)
            for r_item in radius:
                blast_radius_set.add(r_item)
                
            # Add dependency relationships to call graph context
            call_graph_context_set.add(f"Function definition under analysis: {func}")
            callers = G.get_callers(func)
            if callers:
                call_graph_context_set.add(f"  Called by: {', '.join(sorted(callers))}")
            successors = list(G.successors(func))
            if successors:
                call_graph_context_set.add(f"  Calls: {', '.join(sorted(successors))}")

        state["blast_radius"] = sorted(list(blast_radius_set))
        state["call_graph_context"] = sorted(list(call_graph_context_set))
        
        state["investigation_steps"].append({
            "step": "Call Graph Analysis",
            "detail": f"Analyzed call graph for {len(functions_to_check)} functions. Found blast radius of {len(state['blast_radius'])} services.",
            "time": round(time.time() - start_time, 3)
        })
        
    except Exception as e:
        logger.error(f"Failed to analyze call graph: {e}")
        state["investigation_steps"].append({
            "step": "Call Graph Analysis",
            "detail": f"Failed with error: {e}",
            "time": round(time.time() - start_time, 3)
        })
        
    return state
