"""
Planner module for the IncidentIQ Agent.
Responsible for formulating a multi-step diagnostic or recovery plan based on the incident description.
"""

import json
import logging
from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)


DEFAULT_PLAN: List[str] = [
    "Identify the affected services and check recent deployment logs for changes.",
    "Retrieve similar past incident reports from the postmortem database.",
    "Analyze the call graph to map service dependencies and calculate the blast radius.",
    "Search the codebase for the relevant modules and functions named in the logs.",
    "Synthesize findings to suggest a verification plan and fix for the root cause."
]


def generate_plan(anonymized_query: str) -> List[str]:
    """
    Formulates a multi-step diagnostic plan for SRE analysis based on the anonymized query.
    Returns a list of 4-6 investigation steps.

    Args:
        anonymized_query (str): The anonymized query string.

    Returns:
        List[str]: List of 4-6 sequential investigation steps.
    """
    if not anonymized_query:
        return DEFAULT_PLAN
        
    try:
        chat = ChatOllama(model="llama3.1", temperature=0)
        
        system_prompt = (
            "You are an expert SRE analyzing a production incident.\n"
            "Given an anonymized incident description, formulate a JSON list of 4-6 sequential\n"
            "investigation steps. The steps must collectively cover:\n"
            "- Locating the affected code/modules\n"
            "- Looking up past incident postmortems/runbooks\n"
            "- Analyzing the call graph impact / blast radius\n"
            "- Investigating recent changes\n"
            "- Formulating a fix recommendation\n"
            "Return output strictly in JSON format as a list of strings.\n"
            "Example JSON output:\n"
            "[\n"
            '  "Step 1: Check code chunks for DatabasePool usage.",\n'
            '  "Step 2: Lookup similar past connection pool outages.",\n'
            '  "Step 3: Analyze the call graph to determine if ServiceA slowdown propagates.",\n'
            '  "Step 4: Check if db_client connection limits were recently edited.",\n'
            '  "Step 5: Formulate connection limit scaling fix."\n'
            "]\n"
            "Ensure the response is valid JSON and contains nothing else (no conversational filler, no markdown code fences)."
        )
        
        human_prompt = f"Anonymized Incident description:\n\n{anonymized_query}"
        
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
            
        plan = json.loads(raw_content)
        
        if not isinstance(plan, list) or not all(isinstance(step, str) for step in plan):
            raise ValueError("Parsed JSON is not a list of strings.")
            
        return plan
        
    except Exception as e:
        logger.error(f"Failed to generate plan via API: {e}. Falling back to default plan.")
        return DEFAULT_PLAN
