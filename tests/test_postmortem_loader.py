import os
from ingestion.postmortem_loader import load_postmortems_and_runbooks

def test_postmortem_loader() -> None:
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    postmortems_dir = os.path.join(current_dir, "data", "postmortems")
    runbooks_dir = os.path.join(current_dir, "data", "runbooks")
    
    docs = load_postmortems_and_runbooks(postmortems_dir, runbooks_dir)
    assert len(docs) > 0, "No documents loaded"
    
    postmortems = [d for d in docs if d.metadata["type"] == "postmortem"]
    runbooks = [d for d in docs if d.metadata["type"] == "runbook"]
    
    assert len(postmortems) == 4, f"Expected 4 postmortems, got {len(postmortems)}"
    assert len(runbooks) == 3, f"Expected 3 runbooks, got {len(runbooks)}"
    
    # Verify metadata fields are parsed correctly on incident_001.md
    incident_001 = next((p for p in postmortems if "incident_001.md" in p.metadata["filepath"]), None)
    assert incident_001 is not None, "incident_001.md was not loaded"
    
    assert incident_001.metadata["date"] == "2024-11-15"
    assert incident_001.metadata["severity"] == "P0"
    assert incident_001.metadata["mttr"] == 134
    assert "payment" in incident_001.metadata["tags"]
    assert "database" in incident_001.metadata["tags"]
    assert "connection-pool" in incident_001.metadata["tags"]
