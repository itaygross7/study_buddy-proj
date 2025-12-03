"""Tests for the Triple Hybrid AI Client"""
import pytest
from unittest.mock import Mock, patch
from src.services.ai_client import TripleHybridClient, AIClient


def test_triple_hybrid_client_initialization():
    """Test that TripleHybridClient can be initialized"""
    client = TripleHybridClient()
    assert client is not None
    assert hasattr(client, 'route_task')
    assert hasattr(client, 'generate_text')


def test_backward_compatibility():
    """Test that AIClient is backward compatible with TripleHybridClient"""
    client = AIClient()
    assert isinstance(client, TripleHybridClient)
    assert hasattr(client, 'generate_text')


def test_baby_mode_prompt_modification():
    """Test that baby mode modifies prompts correctly"""
    client = TripleHybridClient()
    prompt = "Explain photosynthesis"
    baby_prompt = client._apply_baby_capy_prompt(prompt)
    
    assert "Baby Capy" in baby_prompt
    assert "baby capybara" in baby_prompt
    assert prompt in baby_prompt


def test_route_task_types():
    """Test that different task types can be routed (without making actual API calls)"""
    client = TripleHybridClient()
    
    # Test that the client has the routing method
    assert hasattr(client, 'route_task')
    
    # Test that private methods exist for each model
    assert hasattr(client, '_call_gpt_mini')
    assert hasattr(client, '_call_gpt_4o')
    assert hasattr(client, '_call_gemini_flash')


@patch('src.services.ai_client.openai.OpenAI')
def test_json_mode_enforcement(mock_openai):
    """Test that JSON mode is properly set for quiz tasks"""
    client = TripleHybridClient()
    
    # Mock the OpenAI response
    mock_client_instance = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '{"test": "data"}'
    mock_client_instance.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client_instance
    
    # Initialize OpenAI
    client._openai_initialized = True
    
    # Call with require_json=True
    result = client._call_gpt_mini("Generate quiz", require_json=True)
    
    # Check that the method was called
    assert mock_client_instance.chat.completions.create.called
    call_kwargs = mock_client_instance.chat.completions.create.call_args[1]
    
    # Verify JSON mode was enabled
    assert 'response_format' in call_kwargs
    assert call_kwargs['response_format'] == {"type": "json_object"}


def test_generate_text_parameters():
    """Test that generate_text accepts the new parameters"""
    client = AIClient()
    
    # Test that the method signature accepts all parameters
    import inspect
    sig = inspect.signature(client.generate_text)
    params = sig.parameters
    
    assert 'prompt' in params
    assert 'context' in params
    assert 'task_type' in params
    assert 'require_json' in params
    assert 'baby_mode' in params
