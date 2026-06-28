from unittest.mock import MagicMock, patch
from langchain_core.documents import Document
from agent.graph import run_investigation


@patch("agent.anonymizer.ChatAnthropic")
@patch("agent.planner.ChatAnthropic")
@patch("agent.verifier.ChatAnthropic")
@patch("agent.replanner.ChatAnthropic")
@patch("agent.synthesizer.ChatAnthropic")
@patch("agent.retriever.load_all_stores")
@patch("agent.call_graph_node.os.path.exists")
def test_run_investigation(
    mock_exists: MagicMock,
    mock_load_stores: MagicMock,
    mock_synth_chat: MagicMock,
    mock_replan_chat: MagicMock,
    mock_verify_chat: MagicMock,
    mock_plan_chat: MagicMock,
    mock_anon_chat: MagicMock
) -> None:
    # 1. Mock file exists for call graph node
    mock_exists.return_value = False
    
    # 2. Mock vector stores
    mock_code_doc = Document(
        page_content="def test(): pass",
        metadata={"type": "function", "name": "test", "filepath": "test.py", "line_start": 1}
    )
    mock_store = MagicMock()
    mock_store.similarity_search.return_value = [mock_code_doc]
    mock_load_stores.return_value = {
        "code_chunks": mock_store,
        "summaries": mock_store,
        "incidents": mock_store
    }
    
    # 3. Mock ChatAnthropic responses for anonymize
    mock_anon_instance = MagicMock()
    mock_anon_resp = MagicMock()
    mock_anon_resp.content = '{"anonymized_query": "ServiceA failed", "entity_map": {"ServiceA": "PaymentService"}}'
    mock_anon_instance.invoke.return_value = mock_anon_resp
    mock_anon_chat.return_value = mock_anon_instance
    
    # 4. Mock ChatAnthropic responses for planner
    mock_plan_instance = MagicMock()
    mock_plan_resp = MagicMock()
    mock_plan_resp.content = '["Step 1: Check code", "Step 2: Check incidents"]'
    mock_plan_instance.invoke.return_value = mock_plan_resp
    mock_plan_chat.return_value = mock_plan_instance
    
    # 5. Mock ChatAnthropic responses for verifier
    mock_verify_instance = MagicMock()
    mock_verify_resp = MagicMock()
    mock_verify_resp.content = '{"is_grounded": true, "confidence_score": 0.9, "ungrounded_claims": []}'
    mock_verify_instance.invoke.return_value = mock_verify_resp
    mock_verify_chat.return_value = mock_verify_instance
    
    # 6. Mock ChatAnthropic responses for synthesizer
    mock_synth_instance = MagicMock()
    mock_synth_resp = MagicMock()
    mock_synth_resp.content = """
    {
      "root_cause": "ServiceA database connections ran out.",
      "similar_incidents": [{"title": "DB Outage", "summary": "crashed", "mttr": 10, "date": "2024-01-01"}],
      "suggested_fix": "Increase connections in utils/db_client.py.",
      "final_report": "# final report text"
    }
    """
    mock_synth_instance.invoke.return_value = mock_synth_resp
    mock_synth_chat.return_value = mock_synth_instance

    # 7. Run end-to-end SRE investigation workflow
    final_state = run_investigation("PaymentService is failing")
    
    # Verify de-anonymized and mapped values inside state
    assert final_state["anonymized_query"] == "ServiceA failed"
    assert final_state["entity_map"] == {"ServiceA": "PaymentService"}
    assert final_state["is_grounded"] is True
    assert final_state["root_cause"] == "PaymentService database connections ran out."
    assert final_state["suggested_fix"] == "Increase connections in utils/db_client.py."
    assert final_state["final_report"] == "# final report text"
    assert len(final_state["investigation_steps"]) > 0
