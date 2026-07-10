"""
Build stores script for IncidentIQ.
Initializes the vector databases and call graph index from the source data files and codebase files.
"""

import os
import sys
import pickle
import logging
from dotenv import load_dotenv

from ingestion.ast_chunker import chunk_directory
from ingestion.call_graph import build_call_graph
from ingestion.postmortem_loader import load_postmortems_and_runbooks
from ingestion.vector_store_builder import (
    build_code_chunks_store,
    build_summaries_store,
    build_incidents_store
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    # Load environment variables
    load_dotenv()
    
    # Pre-flight check: Verify API keys are configured
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    missing_keys = []
    if not openai_key or openai_key.startswith("sk-your-key") or "your-key" in openai_key:
        missing_keys.append("OPENAI_API_KEY")
    if not anthropic_key or anthropic_key.startswith("sk-ant-your-key") or "your-key" in anthropic_key:
        missing_keys.append("ANTHROPIC_API_KEY")
        
    if missing_keys:
        logger.error(f"Missing API keys in .env: {', '.join(missing_keys)}")
        print("\n" + "="*80)
        print("ERROR: Missing or placeholder API keys detected in your .env file!")
        print(f"Please configure valid keys for: {', '.join(missing_keys)}")
        print("Once configured, re-run this script to index the codebase and data files.")
        print("="*80 + "\n")
        sys.exit(1)

    # Resolve paths relative to the script location
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sample_codebase_dir = os.path.join(base_dir, "data", "sample_codebase")
    postmortems_dir = os.path.join(base_dir, "data", "postmortems")
    runbooks_dir = os.path.join(base_dir, "data", "runbooks")
    stores_dir = os.path.join(base_dir, "stores")
    
    os.makedirs(stores_dir, exist_ok=True)
    
    logger.info("Starting indexing process for IncidentIQ...")
    
    # 1. Load sample codebase and chunk it
    logger.info("Running AST Chunker over sample codebase...")
    code_docs = chunk_directory(sample_codebase_dir)
    logger.info(f"Generated {len(code_docs)} AST code chunks.")
    
    # 2. Build and save code chunks vector store
    logger.info("Building Code Chunks vector store...")
    code_chunks_path = os.path.join(stores_dir, "code_chunks")
    build_code_chunks_store(code_docs, code_chunks_path)
    
    # 3. Build call graph and pickle it
    logger.info("Building Call Graph dependency graph...")
    G = build_call_graph(sample_codebase_dir)
    call_graph_path = os.path.join(stores_dir, "call_graph.pkl")
    with open(call_graph_path, "wb") as f:
        pickle.dump(G, f)
    logger.info(f"Call Graph built and saved with {len(G.nodes)} nodes and {len(G.edges)} edges.")
    
    # 4. Generate summaries and build summaries vector store
    logger.info("Generating file summaries and building Summaries vector store...")
    summaries_path = os.path.join(stores_dir, "summaries")
    build_summaries_store(sample_codebase_dir, summaries_path)
    
    # 5. Load postmortems & runbooks and build incidents vector store
    logger.info("Loading postmortems and runbooks...")
    incident_docs = load_postmortems_and_runbooks(postmortems_dir, runbooks_dir)
    
    postmortems_count = sum(1 for d in incident_docs if d.metadata.get("type") == "postmortem")
    runbooks_count = sum(1 for d in incident_docs if d.metadata.get("type") == "runbook")
    
    logger.info(f"Loaded {postmortems_count} postmortems and {runbooks_count} runbooks.")
    
    logger.info("Building Incidents/Runbooks vector store...")
    incidents_path = os.path.join(stores_dir, "incidents")
    build_incidents_store(incident_docs, incidents_path)
    
    # Final output summary line
    print(f"Indexed {len(code_docs)} code chunks, {postmortems_count} postmortems, {runbooks_count} runbooks, {len(G.nodes)} call graph nodes.")


if __name__ == "__main__":
    main()
