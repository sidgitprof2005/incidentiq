"""
Vector Store Builder module for IncidentIQ.
Responsible for initializing and building vector stores for codebase chunks, summaries, and postmortems/runbooks.
"""

import os
import logging
from typing import List, Dict, Optional
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import OllamaEmbeddings
from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)


def generate_file_summary(filepath: str, file_content: str) -> Optional[str]:
    """
    Calls the local Ollama API to generate a 3-sentence summary of the Python file content.
    Prevents crashing by catching API errors and returning None.
    """
    try:
        chat = ChatOllama(model="llama3.1", temperature=0)
        system_prompt = (
            "You are an expert SRE. Provide a concise, exactly 3-sentence summary "
            "explaining the purpose, key components, and dependencies of this Python file."
        )
        human_prompt = f"File: {os.path.basename(filepath)}\n\nContent:\n```python\n{file_content}\n```"
        
        response = chat.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
        
        return response.content.strip()
    except Exception as e:
        logger.error(f"Failed to generate summary for {filepath}: {e}")
        return None


def build_code_chunks_store(documents: List[Document], save_path: str) -> FAISS:
    """
    Builds the FAISS store for AST code chunks and saves it locally.
    """
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    os.makedirs(save_path, exist_ok=True)
    db = FAISS.from_documents(documents, embeddings)
    db.save_local(save_path)
    return db


def build_summaries_store(codebase_dir: str, save_path: str) -> Optional[FAISS]:
    """
    Walks codebase directory, calls ChatOllama to generate summaries, builds and saves FAISS store.
    """
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    os.makedirs(save_path, exist_ok=True)
    
    summary_docs: List[Document] = []
    
    for root, _, files in os.walk(codebase_dir):
        for file in sorted(files):
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                logger.info(f"Generating summary for file: {file}")
                summary = generate_file_summary(filepath, content)
                if summary:
                    summary_docs.append(
                        Document(
                            page_content=summary,
                            metadata={"filepath": filepath, "type": "summary", "filename": file}
                        )
                    )
                else:
                    logger.warning(f"Skipping summary index for {file} due to generation error.")

    if not summary_docs:
        logger.error("No summaries were successfully generated. Summaries store will not be created.")
        return None
        
    db = FAISS.from_documents(summary_docs, embeddings)
    db.save_local(save_path)
    return db


def build_incidents_store(documents: List[Document], save_path: str) -> FAISS:
    """
    Builds the FAISS store for incident reports and runbooks, saving it locally.
    """
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    os.makedirs(save_path, exist_ok=True)
    db = FAISS.from_documents(documents, embeddings)
    db.save_local(save_path)
    return db


def load_all_stores(stores_base_dir: str = "stores") -> Dict[str, FAISS]:
    """
    Loads all three vector stores from disk.
    If any store is missing, raises a ValueError indicating that build_stores.py must be run first.
    """
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    
    code_chunks_path = os.path.join(stores_base_dir, "code_chunks")
    summaries_path = os.path.join(stores_base_dir, "summaries")
    incidents_path = os.path.join(stores_base_dir, "incidents")
    
    missing = []
    if not os.path.exists(os.path.join(code_chunks_path, "index.faiss")):
        missing.append("code_chunks")
    if not os.path.exists(os.path.join(summaries_path, "index.faiss")):
        missing.append("summaries")
    if not os.path.exists(os.path.join(incidents_path, "index.faiss")):
        missing.append("incidents")
        
    if missing:
        raise ValueError(
            f"Missing vector store index files for: {', '.join(missing)}. "
            f"Please run 'python build_stores.py' first to build and initialize these stores."
        )
        
    try:
        code_chunks_store = FAISS.load_local(code_chunks_path, embeddings, allow_dangerous_deserialization=True)
        summaries_store = FAISS.load_local(summaries_path, embeddings, allow_dangerous_deserialization=True)
        incidents_store = FAISS.load_local(incidents_path, embeddings, allow_dangerous_deserialization=True)
    except Exception as e:
        raise RuntimeError(f"Error loading FAISS stores from local disk: {e}")
        
    return {
        "code_chunks": code_chunks_store,
        "summaries": summaries_store,
        "incidents": incidents_store
    }
