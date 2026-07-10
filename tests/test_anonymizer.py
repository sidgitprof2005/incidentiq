from unittest.mock import MagicMock, patch
from agent.anonymizer import anonymize, de_anonymize


@patch("agent.anonymizer.ChatOllama")
def test_anonymize_success(mock_chat_class: MagicMock) -> None:
    mock_chat_instance = MagicMock()
    mock_chat_class.return_value = mock_chat_instance
    
    # Mock successful response
    mock_response = MagicMock()
    mock_response.content = """
    ```json
    {
      "anonymized_query": "ServiceA crashed due to database pool exhaustion on DB1.",
      "entity_map": {"ServiceA": "PaymentService", "DB1": "DatabasePool"}
    }
    ```
    """
    mock_chat_instance.invoke.return_value = mock_response
    
    query = "PaymentService crashed due to database pool exhaustion on DatabasePool."
    anon, entity_map = anonymize(query)
    
    assert anon == "ServiceA crashed due to database pool exhaustion on DB1."
    assert entity_map == {"ServiceA": "PaymentService", "DB1": "DatabasePool"}


def test_de_anonymize() -> None:
    anon = "ServiceA crashed due to database pool exhaustion on DB1."
    entity_map = {"ServiceA": "PaymentService", "DB1": "DatabasePool"}
    de_anon = de_anonymize(anon, entity_map)
    assert de_anon == "PaymentService crashed due to database pool exhaustion on DatabasePool."


@patch("agent.anonymizer.ChatOllama")
def test_anonymize_fallback(mock_chat_class: MagicMock) -> None:
    mock_chat_instance = MagicMock()
    mock_chat_class.return_value = mock_chat_instance
    
    # Mock a malformed string response
    mock_response = MagicMock()
    mock_response.content = "Malformed response, not JSON."
    mock_chat_instance.invoke.return_value = mock_response
    
    query = "PaymentService crashed."
    anon, entity_map = anonymize(query)
    
    assert anon == query
    assert entity_map == {}
