import os
from ingestion.call_graph import build_call_graph

def test_call_graph() -> None:
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sample_codebase_dir = os.path.join(current_dir, "data", "sample_codebase")
    
    G = build_call_graph(sample_codebase_dir)
    assert len(G.nodes) > 0, "No nodes in call graph"
    
    # Verify expected nodes are present
    assert "OrderService.create_order" in G.nodes
    assert "PaymentProcessor.process_payment" in G.nodes
    
    # Verify directed edge exists: OrderService.create_order -> PaymentProcessor.process_payment
    assert G.has_edge("OrderService.create_order", "PaymentProcessor.process_payment"), \
        "Edge from OrderService.create_order to PaymentProcessor.process_payment not found"
        
    # Test get_callers helper
    callers = G.get_callers("PaymentProcessor.process_payment")
    assert "OrderService.create_order" in callers
    
    # Test get_affected_functions helper
    affected = G.get_affected_functions("PaymentProcessor.process_payment", depth=1)
    assert "DatabasePool.get_connection" in affected
    assert "CacheClient.get" in affected
    
    # Test get_blast_radius helper
    blast = G.get_blast_radius("PaymentProcessor.process_payment")
    assert len(blast) >= 2
    # Verify formatting (checks for filenames and method names)
    assert any("db_client.py" in item for item in blast)
    assert any("DatabasePool.get_connection" in item for item in blast)
