"""
Replanner module for the IncidentIQ Agent.
Responsible for adjusting the plan dynamically if verification fails or new evidence is uncovered.
"""

import ast
import json
import time
import logging
from typing import List
from agent.state import IncidentState
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)


def replan(state: IncidentState) -> IncidentState:
    """
    Reformulates the remaining plan steps based on ungrounded claims.
    Increments replan_count and records progress.
    Guarantees it never raises an exception.

    Args:
        state (IncidentState): The current agent state.

    Returns:
        IncidentState: The updated agent state.
    """
    start_time = time.time()
    
    # Increment replan count (safe from raising)
    state["replan_count"] = state.get("replan_count", 0) + 1
    
    try:
        # Extract ungrounded claims from the last Verification log
        claims: List[str] = []
        for step in reversed(state.get("investigation_steps", [])):
            if step.get("step") == "Verification":
                detail = step.get("detail", "")
                if "Ungrounded claims:" in detail:
                    raw_claims = detail.split("Ungrounded claims:")[-1].strip()
                    try:
                        claims = ast.literal_eval(raw_claims)
                    except Exception:
                        pass
                break
                
        if not claims:
            state["investigation_steps"].append({
                "step": "Replanning",
                "detail": "No ungrounded claims found. Keeping existing plan.",
                "time": round(time.time() - start_time, 3)
            })
            return state

        # Call local Ollama API to modify plan
        chat = ChatOllama(model="llama3.1", temperature=0)
        
        system_prompt = (
            "You are an SRE replanning assistant.\n"
            "An investigation was started for an incident but failed verification due to missing information.\n"
            "Based on the original query, the current plan, and the list of ungrounded claims (information gaps),\n"
            "generate an updated sequence of 2-3 specific SRE investigation steps to resolve these gaps.\n"
            "Return the updated steps strictly in JSON format as a list of strings.\n"
            "Example JSON:\n"
            "[\n"
            '  "Step 1: Check DatabasePool configuration limits in utils/db_client.py.",\n'
            '  "Step 2: Trace where DatabasePool is initialized in payment_service.py."\n'
            "]\n"
            "Ensure the response is valid JSON and contains nothing else (no conversational filler, no markdown code fences)."
        )
        
        human_prompt = (
            f"Original query: {state.get('anonymized_query', '')}\n\n"
            f"Current plan: {state.get('plan', [])}\n\n"
            f"Ungrounded claims: {claims}"
        )
        
        response = chat.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
        
        raw_content = response.content.strip()
        
        # Defensive JSON parsing
        if raw_content.startswith("```"):
            lines = raw_content.splitlines()
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw_content = "\n".join(lines).strip()
            
        new_steps = json.loads(raw_content)
        if isinstance(new_steps, list) and all(isinstance(s, str) for s in new_steps):
            # Replace remaining plan steps starting from current_step
            current_idx = state.get("current_step", 0)
            state["plan"] = state["plan"][:current_idx] + new_steps
            
            state["investigation_steps"].append({
                "step": "Replanning",
                "detail": f"Replanned successfully. New plan steps: {new_steps}",
                "time": round(time.time() - start_time, 3)
            })
        else:
            raise ValueError("Parsed JSON is not a list of strings.")
            
    except Exception as e:
        logger.error(f"Failed to replan: {e}. Keeping plan unchanged.")
        state["investigation_steps"].append({
            "step": "Replanning",
            "detail": f"Replanning encountered an error: {e}. Keeping existing plan.",
            "time": round(time.time() - start_time, 3)
        })
        
    return state
