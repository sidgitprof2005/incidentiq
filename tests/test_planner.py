from unittest.mock import MagicMock, patch
from agent.planner import generate_plan, DEFAULT_PLAN


@patch("agent.planner.ChatOllama")
def test_generate_plan_success(mock_chat_class: MagicMock) -> None:
    mock_chat_instance = MagicMock()
    mock_chat_class.return_value = mock_chat_instance
    
    # Mock successful response
    mock_response = MagicMock()
    mock_response.content = """
    [
      "Step 1: Check DatabasePool",
      "Step 2: Check similar incidents",
      "Step 3: Analyze call graph",
      "Step 4: Check git log"
    ]
    """
    mock_chat_instance.invoke.return_value = mock_response
    
    plan = generate_plan("ServiceA crashed.")
    assert len(plan) == 4
    assert plan[0] == "Step 1: Check DatabasePool"
    assert plan[3] == "Step 4: Check git log"


@patch("agent.planner.ChatOllama")
def test_generate_plan_fallback(mock_chat_class: MagicMock) -> None:
    mock_chat_instance = MagicMock()
    mock_chat_class.return_value = mock_chat_instance
    
    # Mock API failure
    mock_chat_instance.invoke.side_effect = Exception("API error")
    
    plan = generate_plan("ServiceA crashed.")
    assert plan == DEFAULT_PLAN
