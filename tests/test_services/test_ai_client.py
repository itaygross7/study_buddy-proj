import pytest
from unittest.mock import MagicMock, patch
from src.services.ai_client import AIClient


class TestAIClient:
    """Tests for AIClient with mocked AI services."""

    def test_ai_client_initialization_gemini(self):
        """Test AIClient initialization with Gemini provider."""
        client = AIClient(provider="gemini")
        assert client.provider == "gemini"
        assert client._initialized is False

    def test_ai_client_initialization_openai(self):
        """Test AIClient initialization with OpenAI provider."""
        client = AIClient(provider="openai")
        assert client.provider == "openai"
        assert client._initialized is False

    def test_ai_client_initialization_unsupported(self):
        """Test AIClient initialization with unsupported provider."""
        client = AIClient(provider="unsupported")
        with pytest.raises(ValueError, match="Unsupported AI provider"):
            client._ensure_initialized()

    @patch('src.services.ai_client.genai')
    @patch('src.services.ai_client.settings')
    def test_generate_text_gemini_success(self, mock_settings, mock_genai):
        """Test successful text generation with Gemini."""
        mock_settings.GEMINI_API_KEY = "valid-api-key"
        mock_settings.OPENAI_API_KEY = ""
        mock_settings.SB_GEMINI_MODEL = "gemini-1.5-flash"

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = " Generated response text "
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        client = AIClient(provider="gemini")
        result = client.generate_text("Summarize this", "Some context text")

        assert result == "Generated response text"
        mock_genai.configure.assert_called_once_with(api_key="valid-api-key")
        mock_genai.GenerativeModel.assert_called_once_with('gemini-1.5-flash')

    def test_ensure_initialized_missing_gemini_key(self):
        """Test error when Gemini API key is missing."""
        with patch('src.services.ai_client.settings') as mock_settings:
            mock_settings.GEMINI_API_KEY = ""
            mock_settings.OPENAI_API_KEY = ""

            client = AIClient(provider="gemini")

            with pytest.raises(ValueError, match="Gemini API key is not configured"):
                client._ensure_initialized()

    def test_ensure_initialized_missing_openai_key(self):
        """Test error when OpenAI API key is missing."""
        with patch('src.services.ai_client.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.GEMINI_API_KEY = ""

            client = AIClient(provider="openai")

            with pytest.raises(ValueError, match="OpenAI API key is not configured"):
                client._ensure_initialized()


class TestAISafetyPrompt:
    """Tests for AI safety prompt generation."""

    def test_create_safety_guard_prompt(self):
        """Test that safety instructions are included in the prompt."""
        from sb_utils.ai_safety import create_safety_guard_prompt

        prompt = "Summarize this text"
        context = "This is the document content."

        result = create_safety_guard_prompt(prompt, context)

        assert "IMPORTANT" in result
        assert "educational assistant" in result
        assert context in result
        assert prompt in result
        assert "Do NOT invent facts" in result
