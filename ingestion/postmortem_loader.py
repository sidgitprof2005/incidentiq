"""
Postmortem Loader module for IncidentIQ.
Responsible for reading, parsing, and preprocessing markdown postmortem and runbook files.
"""

import os
import re
from typing import List, Dict, Any
from langchain_core.documents import Document


def parse_postmortem_metadata(content: str, is_postmortem: bool) -> Dict[str, Any]:
    """
    Parses metadata attributes from the file content.
    Extracts type, date, severity, tags, and MTTR.
    """
    metadata: Dict[str, Any] = {
        "type": "postmortem" if is_postmortem else "runbook",
        "date": None,
        "severity": None,
        "tags": [],
        "mttr": None
    }
    
    if not is_postmortem:
        return metadata
        
    # Extract Date: e.g. "Date: 2024-11-15"
    date_match = re.search(r"Date:\s*([\w\-]+)", content, re.IGNORECASE)
    if date_match:
        metadata["date"] = date_match.group(1).strip()
        
    # Extract Severity: e.g. "Severity: P0"
    severity_match = re.search(r"Severity:\s*(P[0-9]+)", content, re.IGNORECASE)
    if severity_match:
        metadata["severity"] = severity_match.group(1).strip()
        
    # Extract MTTR: e.g. "MTTR: 134 min."
    mttr_match = re.search(r"MTTR:\s*([0-9]+)", content, re.IGNORECASE)
    if mttr_match:
        metadata["mttr"] = int(mttr_match.group(1).strip())
        
    # Extract Tags: e.g. "Tags: payment, database"
    tags_match = re.search(r"Tags:\s*([^\n\r]+)", content, re.IGNORECASE)
    if tags_match:
        raw_tags = tags_match.group(1).split(",")
        metadata["tags"] = [tag.strip() for tag in raw_tags if tag.strip()]
        
    return metadata


def load_postmortems_and_runbooks(postmortems_dir: str, runbooks_dir: str) -> List[Document]:
    """
    Loads all .md files from postmortems and runbooks directories and parses metadata.

    Args:
        postmortems_dir (str): Directory containing postmortem reports.
        runbooks_dir (str): Directory containing troubleshooting runbooks.

    Returns:
        List[Document]: List of LangChain Document objects with parsed metadata.
    """
    documents: List[Document] = []
    
    # Process Postmortems
    if os.path.exists(postmortems_dir):
        for file in sorted(os.listdir(postmortems_dir)):
            if file.endswith(".md"):
                filepath = os.path.join(postmortems_dir, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                metadata = parse_postmortem_metadata(content, is_postmortem=True)
                metadata["filepath"] = filepath
                documents.append(Document(page_content=content, metadata=metadata))
                
    # Process Runbooks
    if os.path.exists(runbooks_dir):
        for file in sorted(os.listdir(runbooks_dir)):
            if file.endswith(".md"):
                filepath = os.path.join(runbooks_dir, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                metadata = parse_postmortem_metadata(content, is_postmortem=False)
                metadata["filepath"] = filepath
                documents.append(Document(page_content=content, metadata=metadata))
                
    return documents
