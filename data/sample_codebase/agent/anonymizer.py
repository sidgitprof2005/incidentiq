"""
Anonymizer module for the IncidentIQ Agent.
Responsible for scrubbing sensitive or PII data from postmortems and user queries before processing.
"""

import json
import logging
from typing import Tuple, Dict
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)


def anonymize(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Identifies named entities in a text (e.g. ServiceNames, EngineerNames, SystemNames)
    and replaces them with generic placeholders (ServiceA, Engineer1, System1, etc.).
    Returns (anonymized_query, entity_map).
    """
    if not text:
        return "", {}
        
    try:
        chat = ChatOllama(model="llama3.1", temperature=0)
        
        system_prompt = (
            "You are an SRE anonymization utility. Analyze the given incident query.\n"
            "Identify all specific names of services (e.g., PaymentService, OrderService),\n"
            "engineers, hostnames, databases, or systems, and replace them with generic\n"
            "placeholders (like ServiceA, ServiceB, System1, Engineer1, DB1, etc.).\n"
            "You must return your output strictly in JSON format. The JSON must contain\n"
            "exactly two keys:\n"
            '1. "anonymized_query": The incident query text with placeholders replacing the entities.\n'
            '2. "entity_map": A dictionary where the keys are the placeholders and the values are the original entities.\n'
            "Example JSON:\n"
            "{\n"
            '  "anonymized_query": "ServiceA crashed due to OOM because DB1 pool was exhausted.",\n'
            '  "entity_map": {"ServiceA": "PaymentService", "DB1": "PostgresDB"}\n'
            "}\n"
            "Ensure the response is valid JSON and contains nothing else (no conversational filler, no markdown code fences)."
        )
        
        human_prompt = f"Anonymize this query:\n\n{text}"
        
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
        anonymized_query = data.get("anonymized_query", text)
        entity_map = data.get("entity_map", {})
        
        if not isinstance(anonymized_query, str) or not isinstance(entity_map, dict):
            raise ValueError("Parsed JSON shape is invalid.")
            
        return anonymized_query, entity_map
        
    except Exception as e:
        logger.error(f"Failed to anonymize text: {e}. Falling back to original text.")
        return text, {}


def de_anonymize(text: str, entity_map: Dict[str, str]) -> str:
    """
    Reverses the anonymization substitution in the provided text.
    Replaces all keys (placeholders) in the entity_map with their corresponding values (original names).
    """
    if not text or not entity_map:
        return text
        
    de_anonymized = text
    # Sort keys by length descending to prevent partial substitution
    for placeholder in sorted(entity_map.keys(), key=len, reverse=True):
        original = entity_map[placeholder]
        de_anonymized = de_anonymized.replace(placeholder, original)
        
    return de_anonymized
