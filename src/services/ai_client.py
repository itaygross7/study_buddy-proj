import google.generativeai as genai
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from src.infrastructure.config import settings
from sb_utils.logger_utils import logger
from sb_utils.ai_safety import create_safety_guard_prompt
from src.domain.errors import AIClientError

class AIClient:
    """
    A unified client for interacting with different AI models (OpenAI, Gemini).
    Includes built-in retry logic and safety guards.
    """
    def __init__(self, provider: str = "gemini"):
        self.provider = provider
        self._initialized = False
        
    def _ensure_initialized(self):
        """Lazy initialization of AI provider."""
        if self._initialized:
            return
            
        if self.provider == "openai":
            if not settings.OPENAI_API_KEY or "your_openai" in settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API key is not configured.")
            openai.api_key = settings.OPENAI_API_KEY
        elif self.provider == "gemini":
            if not settings.GEMINI_API_KEY or "your_google" in settings.GEMINI_API_KEY:
                raise ValueError("Gemini API key is not configured.")
            genai.configure(api_key=settings.GEMINI_API_KEY)
        else:
            raise ValueError("Unsupported AI provider specified.")
        self._initialized = True

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def generate_text(self, prompt: str, context: str) -> str:
        """
        Generates text using the selected AI provider, with retries and safety.
        """
        self._ensure_initialized()
        full_prompt = create_safety_guard_prompt(prompt, context)
        
        try:
            if self.provider == "openai":
                response = openai.Completion.create(
                    engine="text-davinci-003",
                    prompt=full_prompt,
                    max_tokens=1500,
                    temperature=0.7,
                    timeout=30.0,  # Added timeout
                )
                return response.choices[0].text.strip()
            
            elif self.provider == "gemini":
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(
                    full_prompt,
                    request_options={"timeout": 45.0} # Added timeout
                )
                return response.text.strip()

        except Exception as e:
            logger.error(f"AI generation failed for provider {self.provider}: {e}", exc_info=True)
            raise AIClientError(f"The AI service failed to process the request: {e}") from e

        raise AIClientError("The AI service returned an empty or invalid response.")

# Default client instance (lazy initialization)
ai_client = AIClient(provider="gemini")
