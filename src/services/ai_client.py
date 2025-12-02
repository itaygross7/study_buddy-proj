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

    Model selection is configurable via environment variables:
    - SB_OPENAI_MODEL: OpenAI model to use (default: gpt-4o-mini)
    - SB_GEMINI_MODEL: Gemini model to use (default: gemini-1.5-flash)
    - SB_DEFAULT_PROVIDER: Default AI provider (default: gemini)
    - SB_BASE_URL: Optional custom base URL for API
    """

    def __init__(self, provider: str = None):
        self.provider = provider or settings.SB_DEFAULT_PROVIDER
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of AI provider."""
        if self._initialized:
            return

        if self.provider == "openai":
            if not settings.OPENAI_API_KEY or "your_openai" in settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API key is not configured.")
            openai.api_key = settings.OPENAI_API_KEY
            # Set custom base URL if provided
            if settings.SB_BASE_URL:
                openai.api_base = settings.SB_BASE_URL
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
        Uses configurable model names from SB_* environment variables.
        """
        self._ensure_initialized()
        full_prompt = create_safety_guard_prompt(prompt, context)

        try:
            if self.provider == "openai":
                model_name = settings.SB_OPENAI_MODEL
                logger.debug(f"Using OpenAI model: {model_name}")

                client = openai.OpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.SB_BASE_URL if settings.SB_BASE_URL else None,
                    timeout=30.0
                )
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": full_prompt}],
                    max_tokens=1500,
                    temperature=0.7,
                )
                return response.choices[0].message.content.strip()

            elif self.provider == "gemini":
                model_name = settings.SB_GEMINI_MODEL
                logger.debug(f"Using Gemini model: {model_name}")

                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    full_prompt,
                    request_options={"timeout": 45.0}
                )
                return response.text.strip()

        except Exception as e:
            logger.error(f"AI generation failed for provider {self.provider}: {e}", exc_info=True)
            raise AIClientError(f"The AI service failed to process the request: {e}") from e

        raise AIClientError("The AI service returned an empty or invalid response.")


# Default client instance (lazy initialization)
ai_client = AIClient(provider=settings.SB_DEFAULT_PROVIDER)
