"""
Synthesizer module for the IncidentIQ Agent.
Responsible for assembling the final findings, diagnosis, and action plan into a clean presentation format.
"""

import os
import json
import time
import logging
from typing import Dict, Any, List
from agent.state import IncidentState
from agent.anonymizer import de_anonymize
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)


def synthesize(state: IncidentState) -> IncidentState:
    """
    Synthesizes the final investigation report, root cause, suggested fix, 
    and blast radius by querying Claude. De-anonymizes the generated texts 
    using state["entity_map"] before return.

    Args:
        state (IncidentState): The current agent state.

    Returns:
        IncidentState: The updated agent state.
    """
    start_time = time.time()
    entity_map = state.get("entity_map", {})
    
    # 1. Deduplicate citations
    citations = list(set(state.get("citations", [])))
    
    # 2. Build context parameters
    retrieved_context = state.get("retrieved_context", [])
    call_graph_context = state.get("call_graph_context", [])
    
    context_str = ""
    for i, ctx in enumerate(retrieved_context):
        content = ctx.get("content", "")
        meta = ctx.get("metadata", {})
        filepath = meta.get("filepath", "unknown")
        context_str += f"\nDocument {i+1} (Source: {filepath}):\n{content}\n"
        
    call_graph_str = "\n".join(call_graph_context)

    try:
        chat = ChatOllama(model="llama3.1", temperature=0)
        
        system_prompt = (
            "You are an expert SRE synthesizing an incident investigation report.\n"
            "Based on the provided retrieved context and call graph details, identify the root cause,\n"
            "similar past incidents, a suggested code fix, and construct a full markdown final report.\n"
            "Your output must be strictly in JSON format with these exact keys:\n"
            '1. "root_cause": 2-3 concise, grounded sentences explaining the failure mechanism.\n'
            '2. "similar_incidents": a list of objects, each with "title" (str), "summary" (str), "mttr" (str/int), and "date" (str).\n'
            '3. "suggested_fix": a string detailing the specific file, line number, and exact code change required.\n'
            '4. "final_report": a comprehensive markdown report summarizing: Executive Summary, Root Cause,\n'
            "Timeline (if known), Suggested Fix, Blast Radius, and Action Items.\n"
            "Format the JSON correctly and do not include conversational filler or markdown fences."
        )
        
        human_prompt = (
            f"Anonymized Query: {state.get('anonymized_query', '')}\n\n"
            f"Retrieved Context Documents:\n{context_str}\n\n"
            f"Call Graph Context:\n{call_graph_str}"
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
        root_cause = data.get("root_cause", "")
        similar_incidents = data.get("similar_incidents", [])
        suggested_fix = data.get("suggested_fix", "")
        final_report = data.get("final_report", "")
        
    except Exception as e:
        logger.error(f"Failed to synthesize report via API: {e}. Falling back to default generation.")
        # Construct fallback content
        pm_titles = []
        for ctx in retrieved_context:
            meta = ctx.get("metadata", {})
            if meta.get("type") == "postmortem":
                title_match = meta.get("filepath", "Incident")
                pm_titles.append(os.path.basename(title_match))
                
        root_cause = (
            "Synthesis failed due to API limits or errors. Potential root cause indicates "
            "database connection pool exhaustion or cache memory leaks based on retrieved context."
        )
        similar_incidents = [
            {"title": title, "summary": "Outage details available in postmortem reports.", "mttr": "unknown", "date": "unknown"}
            for title in pm_titles
        ]
        suggested_fix = (
            "Review codebase connection parameters in utils/db_client.py or LRU cache size "
            "limits in utils/cache_client.py."
        )
        final_report = (
            "# SRE Investigation Report (Fallback)\n\n"
            "## Executive Summary\n"
            "Automated synthesis failed due to system/API error. Below are the partial findings.\n\n"
            "## Potential Root Cause\n"
            f"{root_cause}\n\n"
            "## Suggested Fix Action\n"
            f"{suggested_fix}\n\n"
            "## Blast Radius\n"
            f"{', '.join(state.get('blast_radius', []))}\n"
        )

    # 3. De-anonymize all fields
    de_root_cause = de_anonymize(root_cause, entity_map)
    de_suggested_fix = de_anonymize(suggested_fix, entity_map)
    de_final_report = de_anonymize(final_report, entity_map)
    
    de_similar_incidents: List[Dict[str, Any]] = []
    for inc in similar_incidents:
        de_similar_incidents.append({
            "title": de_anonymize(inc.get("title", ""), entity_map),
            "summary": de_anonymize(inc.get("summary", ""), entity_map),
            "mttr": inc.get("mttr", "unknown"),
            "date": inc.get("date", "unknown")
        })
        
    de_blast_radius = [de_anonymize(b, entity_map) for b in state.get("blast_radius", [])]
    de_citations = [de_anonymize(c, entity_map) for c in citations]
    
    # Store de-anonymized fields back in the state
    state["root_cause"] = de_root_cause
    state["suggested_fix"] = de_suggested_fix
    state["final_report"] = de_final_report
    state["similar_incidents"] = de_similar_incidents
    state["blast_radius"] = de_blast_radius
    state["citations"] = de_citations
    
    state["investigation_steps"].append({
        "step": "Synthesis",
        "detail": "Synthesized final SRE report and de-anonymized all private entity fields.",
        "time": round(time.time() - start_time, 3)
    })
    
    return state
