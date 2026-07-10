import os
from ingestion.postmortem_loader import load_postmortems_and_runbooks

def test_postmortem_loader() -> None:
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    postmortems_dir = os.path.join(current_dir, "data", "postmortems")
    runbooks_dir = os.path.join(current_dir, "data", "runbooks")
    
    docs = load_postmortems_and_runbooks(postmortems_dir, runbooks_dir)
    assert len(docs) > 0, "No documents loaded"
    
    # 1. Assert navigation index.md files are completely skipped
    index_docs = [d for d in docs if "index.md" in os.path.basename(d.metadata.get("filepath", ""))]
    assert len(index_docs) == 0, "index.md files should be excluded from loader output"
    
    postmortems = [d for d in docs if d.metadata["type"] == "postmortem"]
    runbooks = [d for d in docs if d.metadata["type"] == "runbook"]
    
    assert len(postmortems) == 4, f"Expected 4 postmortems, got {len(postmortems)}"
    assert len(runbooks) == 3, f"Expected 3 runbooks, got {len(runbooks)}"
    
    # 2. Verify metadata fields and types are parsed correctly for a postmortem (incident_001.md)
    incident_001 = next((p for p in postmortems if "incident_001.md" in p.metadata["filepath"]), None)
    assert incident_001 is not None, "incident_001.md was not loaded"
    
    assert incident_001.metadata["type"] == "postmortem"
    assert incident_001.metadata["date"] == "2024-11-15"
    assert incident_001.metadata["severity"] == "P0"
    assert isinstance(incident_001.metadata["mttr"], int)
    assert incident_001.metadata["mttr"] == 134
    
    assert isinstance(incident_001.metadata["tags"], list)
    assert "payment" in incident_001.metadata["tags"]
    assert "database" in incident_001.metadata["tags"]
    assert "connection-pool" in incident_001.metadata["tags"]
    
    # Check body content is correctly loaded and doesn't contain raw YAML frontmatter markup
    assert "---" not in incident_001.page_content
    assert "Summary: Payment processing failed" in incident_001.page_content
    
    # 3. Verify metadata fields are parsed correctly on connection_pool.md (Runbook)
    connection_pool_runbook = next((r for r in runbooks if "connection_pool.md" in r.metadata["filepath"]), None)
    assert connection_pool_runbook is not None, "connection_pool.md was not loaded"
    
    assert connection_pool_runbook.metadata["type"] == "runbook"
    assert connection_pool_runbook.metadata["title"] == "Connection Pool Exhaustion"
    assert isinstance(connection_pool_runbook.metadata["tags"], list)
    assert "connection-pool" in connection_pool_runbook.metadata["tags"]
