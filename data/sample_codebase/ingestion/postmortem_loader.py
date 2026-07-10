"""
Postmortem Loader module for IncidentIQ.
Responsible for reading, parsing, and preprocessing markdown postmortem and runbook files.
Supports Google's Open Knowledge Format (OKF v0.1) with YAML frontmatter.
"""

import os
import re
import frontmatter
from typing import List, Dict, Any
from langchain_core.documents import Document


def parse_postmortem_metadata(content: str, is_postmortem: bool) -> Dict[str, Any]:
    """
    Fallback regex parser when frontmatter is missing or incomplete.
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
    Loads all .md files from postmortems and runbooks directories.
    First parses using python-frontmatter (OKF style).
    Falls back to regex-parsing if frontmatter is missing or incorrect.
    Skips navigation index.md files.

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
            if file == "index.md":
                continue
            if file.endswith(".md"):
                filepath = os.path.join(postmortems_dir, file)
                try:
                    # Parse using frontmatter
                    post = frontmatter.load(filepath)
                    metadata = dict(post.metadata)
                    body = post.content
                    
                    required_fields = ["type", "title", "date", "severity", "duration", "mttr", "tags", "resource"]
                    if not all(field in metadata for field in required_fields):
                        raise ValueError("Missing required frontmatter fields")
                        
                    # Normalize type to postmortem/runbook
                    doc_type = metadata.get("type", "")
                    if doc_type in ("Incident", "incident", "postmortem"):
                        metadata["type"] = "postmortem"
                    elif doc_type in ("Runbook", "runbook"):
                        metadata["type"] = "runbook"
                        
                    # Normalize tags
                    tags = metadata.get("tags", [])
                    if isinstance(tags, str):
                        metadata["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
                    elif isinstance(tags, list):
                        metadata["tags"] = [str(t).strip() for t in tags if str(t).strip()]
                    else:
                        metadata["tags"] = []
                        
                    # Normalize mttr
                    if "mttr" in metadata:
                        metadata["mttr"] = int(metadata["mttr"])
                        
                    # Normalize date
                    date_val = metadata.get("date")
                    if date_val is not None:
                        if hasattr(date_val, "strftime"):
                            metadata["date"] = date_val.strftime("%Y-%m-%d")
                        else:
                            metadata["date"] = str(date_val).strip()
                            
                    metadata["filepath"] = filepath
                    documents.append(Document(page_content=body, metadata=metadata))
                    
                except Exception:
                    # Fallback to regex
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    metadata = parse_postmortem_metadata(content, is_postmortem=True)
                    metadata["filepath"] = filepath
                    documents.append(Document(page_content=content, metadata=metadata))
                    
    # Process Runbooks
    if os.path.exists(runbooks_dir):
        for file in sorted(os.listdir(runbooks_dir)):
            if file == "index.md":
                continue
            if file.endswith(".md"):
                filepath = os.path.join(runbooks_dir, file)
                try:
                    # Parse using frontmatter
                    post = frontmatter.load(filepath)
                    metadata = dict(post.metadata)
                    body = post.content
                    
                    required_fields = ["type", "title", "tags", "resource"]
                    if not all(field in metadata for field in required_fields):
                        raise ValueError("Missing required frontmatter fields")
                        
                    # Normalize type to postmortem/runbook
                    doc_type = metadata.get("type", "")
                    if doc_type in ("Incident", "incident", "postmortem"):
                        metadata["type"] = "postmortem"
                    elif doc_type in ("Runbook", "runbook"):
                        metadata["type"] = "runbook"
                        
                    # Normalize tags
                    tags = metadata.get("tags", [])
                    if isinstance(tags, str):
                        metadata["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
                    elif isinstance(tags, list):
                        metadata["tags"] = [str(t).strip() for t in tags if str(t).strip()]
                    else:
                        metadata["tags"] = []
                        
                    metadata["filepath"] = filepath
                    documents.append(Document(page_content=body, metadata=metadata))
                    
                except Exception:
                    # Fallback to regex
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    metadata = parse_postmortem_metadata(content, is_postmortem=False)
                    metadata["filepath"] = filepath
                    documents.append(Document(page_content=content, metadata=metadata))
                    
    return documents
