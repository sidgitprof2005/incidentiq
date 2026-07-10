import os
from ingestion.ast_chunker import chunk_directory

def test_chunk_directory() -> None:
    # Get current directory and resolve path to data/sample_codebase
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sample_codebase_dir = os.path.join(current_dir, "data", "sample_codebase")
    
    chunks = chunk_directory(sample_codebase_dir)
    assert len(chunks) > 0, "No chunks found in sample codebase"
    
    # Assert that PaymentProcessor.process_payment is found as a chunk
    found_process_payment = False
    for chunk in chunks:
        metadata = chunk.metadata
        if (metadata["type"] == "method" and 
            metadata["name"] == "process_payment" and 
            metadata["class_name"] == "PaymentProcessor"):
            found_process_payment = True
            assert "def process_payment" in chunk.page_content
            assert "payment_service.py" in metadata["filepath"]
            assert metadata["line_start"] > 0
            assert metadata["line_end"] >= metadata["line_start"]
            break

    assert found_process_payment, "PaymentProcessor.process_payment chunk was not found"
