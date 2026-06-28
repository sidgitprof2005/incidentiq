"""
Verifier module for the IncidentIQ Agent.
Responsible for checking validity of proposed solutions or diagnostic steps against the codebase.
"""

import json
import logging
import time
from agent.state import IncidentState
from langchain_core.messages import SystemMessage, HumanMessage
from agent.mock_llm import MockChatAnthropic as ChatAnthropic

logger = logging.getLogger(__name__)


def verify(state: IncidentState) -> IncidentState:
    """
    Verifies if the retrieved context contains sufficient information to address the incident description.
    Updates the grounded status in state and details in investigation steps.
    Forces is_grounded to True if replan_count exceeds 3 to avoid infinite loops.

    Args:
        state (IncidentState): The current agent state.

    Returns:
        IncidentState: The verified agent state.
    """
    start_time = time.time()
    
    # Pre-flight check: If replan_count > 3, force grounded to prevent infinite loops
    if state.get("replan_count", 0) >= 3:
        logger.warning("Replan count exceeded limit. Forcing is_grounded = True to guarantee loop termination.")
        state["is_grounded"] = True
        state["investigation_steps"].append({
            "step": "Verification",
            "detail": "Forced grounded status to True because replan count reached the limit of 3.",
            "time": round(time.time() - start_time, 3)
        })
        return state

    anonymized_query = state.get("anonymized_query", "")
    retrieved_context = state.get("retrieved_context", [])
    
    if not anonymized_query or not retrieved_context:
        state["is_grounded"] = False
        state["investigation_steps"].append({
            "step": "Verification",
            "detail": "Verification failed: query or retrieved context is empty. Grounded: False. Confidence: 0.0. Ungrounded claims: ['Missing query or context documentation.']",
            "time": round(time.time() - start_time, 3)
        })
        return state

    try:
        chat = ChatAnthropic(model="claude-sonnet-4-6")
        
        system_prompt = (
            "You are an SRE verification assistant.\n"
            "Analyze the anonymized incident query and the retrieved context documents.\n"
            "Determine if the retrieved context contains sufficient information to identify the root cause "
            "and suggest a specific line-level code fix for the incident.\n"
            "Return your assessment strictly in JSON format with exactly three keys:\n"
            '1. "is_grounded": boolean (true if the context is sufficient, false if critical information is missing).\n'
            '2. "confidence_score": float (0.0 to 1.0 representing your confidence in this decision).\n'
            '3. "ungrounded_claims": list of strings listing any unresolved questions or missing information '
            '(e.g., \"Need details on DatabasePool max connections limit in utils/db_client.py\").\n'
            "Example JSON:\n"
            "{\n"
            '  "is_grounded": false,\n'
            '  "confidence_score": 0.5,\n'
            '  "ungrounded_claims": [\"Need definitions for cache get/set methods in utils/cache_client.py\"]\n'
            "}\n"
            "Ensure the response is valid JSON and contains nothing else (no conversational filler, no markdown code fences)."
        )
        
        # Format the retrieved context for the model
        context_str = ""
        for i, ctx in enumerate(retrieved_context):
            content = ctx.get("content", "")
            meta = ctx.get("metadata", {})
            filepath = meta.get("filepath", "unknown")
            context_str += f"\nDocument {i+1} (Source: {filepath}):\n{content}\n"
            
        human_prompt = (
            f"Incident Query: {anonymized_query}\n\n"
            f"Retrieved Context:\n{context_str}"
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
            
        data = json.loads(raw_content)
        is_grounded = bool(data.get("is_grounded", False))
        confidence_score = float(data.get("confidence_score", 0.0))
        ungrounded_claims = data.get("ungrounded_claims", [])
        
        state["is_grounded"] = is_grounded
        
        detail_msg = (
            f"Grounded: {is_grounded}. Confidence: {confidence_score}. "
            f"Ungrounded claims: {ungrounded_claims}"
        )
        
        state["investigation_steps"].append({
            "step": "Verification",
            "detail": detail_msg,
            "time": round(time.time() - start_time, 3)
        })
        
    except Exception as e:
        logger.error(f"Failed to verify retrieved context: {e}")
        state["is_grounded"] = False
        state["investigation_steps"].append({
            "step": "Verification",
            "detail": f"Verification encountered an error: {e}. Defaulting to Grounded: False.",
            "time": round(time.time() - start_time, 3)
        })
        
    return state
