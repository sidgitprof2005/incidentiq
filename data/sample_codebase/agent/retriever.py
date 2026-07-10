"""
Retriever module for the IncidentIQ Agent.
Responsible for fetching contextually relevant postmortems, codebase snippets, and runbooks.
"""

import os
import time
import logging
from typing import List, Dict, Any, Set
from langchain_core.documents import Document
from agent.state import IncidentState
from ingestion.vector_store_builder import load_all_stores

logger = logging.getLogger(__name__)


def clean_filepath(filepath: str) -> str:
    """
    Cleans filepaths to present simple relative paths or basenames in citations.
    """
    if not filepath:
        return "unknown"
    if "sample_codebase/" in filepath:
        return filepath.split("sample_codebase/")[-1]
    if "postmortems/" in filepath:
        return f"postmortems/{os.path.basename(filepath)}"
    if "runbooks/" in filepath:
        return f"runbooks/{os.path.basename(filepath)}"
    return os.path.basename(filepath)


def parse_doc_title(doc: Document) -> str:
    """
    Extracts the document title from page content or metadata.
    """
    title = doc.metadata.get("title")
    if title:
        return title
        
    lines = doc.page_content.splitlines()
    first_line = lines[0] if lines else ""
    
    if "Title:" in first_line:
        # Extract everything after Title: but before next metadata item like Date or Severity
        parts = first_line.split("Title:")[-1]
        for key in ["Date:", "Severity:", "Duration:", "MTTR:"]:
            if key in parts:
                parts = parts.split(key)[0]
        return parts.strip().rstrip(".").rstrip(",")
    if first_line.startswith("#"):
        return first_line.replace("#", "").replace("Runbook:", "").strip()
        
    return os.path.basename(doc.metadata.get("filepath", "unknown"))


def format_citation(doc: Document) -> str:
    """
    Generates citation string for retrieved documents based on their type.
    """
    meta = doc.metadata
    doc_type = meta.get("type")
    
    if doc_type in ("method", "function", "class"):
        filepath = clean_filepath(meta.get("filepath", ""))
        class_name = meta.get("class_name")
        name = meta.get("name", "unknown")
        line_start = meta.get("line_start", 1)
        if class_name:
            return f"{filepath}::{class_name}.{name}() (line {line_start})"
        return f"{filepath}::{name}() (line {line_start})"
        
    elif doc_type in ("postmortem", "runbook"):
        title = parse_doc_title(doc)
        if doc_type == "postmortem":
            date = meta.get("date", "unknown")
            return f"Incident Report: {title} ({date})"
        return f"Runbook: {title}"
        
    return clean_filepath(meta.get("filepath", ""))


def retrieve(state: IncidentState) -> IncidentState:
    """
    Executes similarity search on the FAISS stores based on the plan steps.
    Always includes incident retrieval as well.
    """
    start_time = time.time()
    
    # Load FAISS stores
    try:
        stores = load_all_stores()
    except Exception as e:
        logger.error(f"Failed to load vector stores: {e}")
        state["investigation_steps"].append({
            "step": "Retrieving context",
            "detail": f"Failed to load vector stores: {e}",
            "time": round(time.time() - start_time, 3)
        })
        return state

    retrieved_docs: List[Document] = []
    seen_content: Set[str] = set()

    def add_unique_docs(docs: List[Document]) -> None:
        for doc in docs:
            if doc.page_content not in seen_content:
                seen_content.add(doc.page_content)
                retrieved_docs.append(doc)

    # 1. Query stores based on plan steps
    for step in state.get("plan", []):
        step_lower = step.lower()
        
        # Route query to correct store
        if any(keyword in step_lower for keyword in ["code", "function", "method", "class", "implement", "service", "processor", "pool", "limit"]):
            store = stores.get("code_chunks")
        elif any(keyword in step_lower for keyword in ["summary", "summaries", "overview", "architecture"]):
            store = stores.get("summaries")
        elif any(keyword in step_lower for keyword in ["incident", "postmortem", "runbook", "past", "outage", "similar"]):
            store = stores.get("incidents")
        else:
            store = stores.get("code_chunks")
            
        if store:
            try:
                results = store.similarity_search(step, k=3)
                add_unique_docs(results)
            except Exception as e:
                logger.error(f"Error querying store for step '{step}': {e}")

    # 2. Always query incidents_store for similar past incidents using anonymized query
    incidents_store = stores.get("incidents")
    if incidents_store and state.get("anonymized_query"):
        try:
            results = incidents_store.similarity_search(state["anonymized_query"], k=3)
            add_unique_docs(results)
        except Exception as e:
            logger.error(f"Error querying incidents store: {e}")

    # Append results to retrieved_context
    retrieved_context_dicts = [
        {"content": doc.page_content, "metadata": doc.metadata}
        for doc in retrieved_docs
    ]
    state["retrieved_context"].extend(retrieved_context_dicts)

    # Build and append citations
    new_citations = [format_citation(doc) for doc in retrieved_docs]
    # Deduplicate citations while preserving order
    for citation in new_citations:
        if citation not in state["citations"]:
            state["citations"].append(citation)

    # Record investigation step
    duration = time.time() - start_time
    state["investigation_steps"].append({
        "step": "Retrieving context",
        "detail": f"Retrieved {len(retrieved_docs)} distinct context documents and updated citations.",
        "time": round(duration, 3)
    })

    return state
