"""
State definition module for the IncidentIQ Agent.
Defines the structure of the shared state used throughout the LangGraph agent execution.
"""

from typing import TypedDict, List, Optional, Dict, Any


class IncidentState(TypedDict):
    incident_description: str
    error_logs: Optional[str]
    affected_service: Optional[str]
    anonymized_query: str
    entity_map: dict
    plan: List[str]
    current_step: int
    retrieved_context: List[dict]
    call_graph_context: List[str]
    is_grounded: bool
    replan_count: int
    root_cause: Optional[str]
    similar_incidents: List[dict]
    suggested_fix: Optional[str]
    blast_radius: List[str]
    citations: List[str]
    final_report: Optional[str]
    investigation_steps: List[dict]


def new_incident_state(incident_description: str, error_logs: Optional[str] = None) -> IncidentState:
    """
    Returns a correctly-initialized empty IncidentState.

    Args:
        incident_description (str): Description of the incident.
        error_logs (Optional[str]): Accompanying stack traces or logs, if any.

    Returns:
        IncidentState: Initial state for the workflow.
    """
    return {
        "incident_description": incident_description,
        "error_logs": error_logs,
        "affected_service": None,
        "anonymized_query": "",
        "entity_map": {},
        "plan": [],
        "current_step": 0,
        "retrieved_context": [],
        "call_graph_context": [],
        "is_grounded": False,
        "replan_count": 0,
        "root_cause": None,
        "similar_incidents": [],
        "suggested_fix": None,
        "blast_radius": [],
        "citations": [],
        "final_report": None,
        "investigation_steps": []
    }
