from unittest.mock import MagicMock, patch
from langchain_core.documents import Document
from agent.state import new_incident_state
from agent.retriever import retrieve


def test_retrieve_logic() -> None:
    # 1. Mock Document targets
    mock_code_doc = Document(
        page_content="def process_payment():\n  pass",
        metadata={
            "type": "method",
            "name": "process_payment",
            "class_name": "PaymentProcessor",
            "filepath": "/path/to/sample_codebase/services/payment_service.py",
            "line_start": 10
        }
    )
    
    mock_incident_doc = Document(
        page_content="Title: Payment Outage. Date: 2024-11-15\nSummary: failed",
        metadata={
            "type": "postmortem",
            "date": "2024-11-15",
            "filepath": "/path/to/postmortems/incident_001.md"
        }
    )
    
    # 2. Mock FAISS stores
    mock_code_store = MagicMock()
    mock_code_store.similarity_search.return_value = [mock_code_doc]
    
    mock_incident_store = MagicMock()
    mock_incident_store.similarity_search.return_value = [mock_incident_doc]
    
    mock_summary_store = MagicMock()
    mock_summary_store.similarity_search.return_value = []
    
    mock_stores = {
        "code_chunks": mock_code_store,
        "summaries": mock_summary_store,
        "incidents": mock_incident_store
    }
    
    # 3. Patch load_all_stores and run retrieve
    with patch("agent.retriever.load_all_stores", return_value=mock_stores):
        state = new_incident_state("Payment service is failing")
        state["anonymized_query"] = "ServiceA is failing"
        state["plan"] = [
            "Check the code for PaymentProcessor"  # triggers code_chunks store
        ]
        
        updated_state = retrieve(state)
        
        # Verify similarity searches were called
        mock_code_store.similarity_search.assert_called_once_with("Check the code for PaymentProcessor", k=3)
        # Verify incidents_store was called for the anonymized query, even though plan step didn't request incidents
        mock_incident_store.similarity_search.assert_called_once_with("ServiceA is failing", k=3)
        
        # Verify retrieved context contains correct values
        retrieved_contents = [d["content"] for d in updated_state["retrieved_context"]]
        assert "def process_payment():\n  pass" in retrieved_contents
        assert "Title: Payment Outage. Date: 2024-11-15\nSummary: failed" in retrieved_contents
        
        # Verify correct citation formatting
        citations = updated_state["citations"]
        assert "services/payment_service.py::PaymentProcessor.process_payment() (line 10)" in citations
        assert "Incident Report: Payment Outage (2024-11-15)" in citations
