import google.generativeai as genai
import openai
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional, Literal
import os

from src.infrastructure.config import settings
from sb_utils.logger_utils import logger
from sb_utils.ai_safety import create_safety_guard_prompt
from src.domain.errors import AIClientError


TaskType = Literal["heavy_file", "quiz", "standard", "complex_reasoning", "baby_capy"]


class TripleHybridClient:
    """
    Triple Hybrid AI Client - Routes tasks to the optimal model for cost and performance.
    
    Routing Strategy:
    - Heavy files (audio/long PDF): Gemini 1.5 Flash (native multimodal)
    - Quiz generation: GPT-4o-mini with JSON enforcement
    - Baby Capy mode: GPT-4o-mini with simplified prompt
    - Standard tasks: GPT-4o-mini
    - Complex reasoning: GPT-4o
    
    Model selection is configurable via environment variables:
    - SB_OPENAI_MODEL: OpenAI model to use (default: gpt-4o-mini)
    - SB_GEMINI_MODEL: Gemini model to use (default: gemini-1.5-flash)
    - SB_DEFAULT_PROVIDER: Default AI provider (default: gemini)
    - SB_BASE_URL: Optional custom base URL for API
    """

    def __init__(self, provider: str = None):
        self.provider = provider or settings.SB_DEFAULT_PROVIDER
        self._openai_initialized = False
        self._gemini_initialized = False

    def _ensure_openai_initialized(self):
        """Lazy initialization of OpenAI provider."""
        if self._openai_initialized:
            return
        
        if not settings.OPENAI_API_KEY or "your_openai" in settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is not configured.")
        self._openai_initialized = True

    def _ensure_gemini_initialized(self):
        """Lazy initialization of Gemini provider."""
        if self._gemini_initialized:
            return
        
        if not settings.GEMINI_API_KEY or "your_google" in settings.GEMINI_API_KEY:
            raise ValueError("Gemini API key is not configured.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._gemini_initialized = True

    def route_task(self, task_type: TaskType, content: str, file_path: Optional[str] = None,
                   require_json: bool = False, baby_mode: bool = False) -> str:
        """
        Smart router that selects the best model for the task.
        
        Args:
            task_type: Type of task to perform
            content: The content/prompt to process
            file_path: Optional file path for multimodal tasks
            require_json: Whether to enforce JSON output (OpenAI only)
            baby_mode: Whether to use Baby Capy simplified explanations
            
        Returns:
            Generated text from the AI model
        """
        if baby_mode or task_type == "baby_capy":
            return self._call_gpt_mini(content, require_json=False, baby_mode=True)
        elif task_type == "heavy_file":
            return self._call_gemini_flash(content, file_path)
        elif task_type == "quiz":
            return self._call_gpt_mini(content, require_json=True)
        elif task_type == "complex_reasoning":
            return self._call_gpt_4o(content)
        else:  # standard
            return self._call_gpt_mini(content, require_json=require_json)

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def _call_gpt_mini(self, prompt: str, require_json: bool = False, baby_mode: bool = False) -> str:
        """Call GPT-4o-mini for standard and quiz tasks."""
        self._ensure_openai_initialized()
        
        # Apply Baby Capy mode prompt modification
        if baby_mode:
            prompt = self._apply_baby_capy_prompt(prompt)
        
        full_prompt = create_safety_guard_prompt(prompt, "")
        
        try:
            client = openai.OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.SB_BASE_URL if settings.SB_BASE_URL else None,
                timeout=30.0
            )
            
            kwargs = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": full_prompt}],
                "max_tokens": 1500,
                "temperature": 0.7,
            }
            
            # Enable JSON mode for quiz generation
            if require_json:
                kwargs["response_format"] = {"type": "json_object"}
                # Ensure prompt asks for JSON
                if "json" not in full_prompt.lower():
                    kwargs["messages"][0]["content"] = full_prompt + "\nReturn your response as valid JSON."
            
            logger.debug(f"Using GPT-4o-mini (JSON mode: {require_json}, Baby mode: {baby_mode})")
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"GPT-4o-mini call failed: {e}", exc_info=True)
            raise AIClientError(f"The AI service failed to process the request: {e}") from e

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def _call_gpt_4o(self, prompt: str) -> str:
        """Call GPT-4o for complex reasoning tasks."""
        self._ensure_openai_initialized()
        full_prompt = create_safety_guard_prompt(prompt, "")
        
        try:
            client = openai.OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.SB_BASE_URL if settings.SB_BASE_URL else None,
                timeout=60.0
            )
            
            logger.debug("Using GPT-4o for complex reasoning")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": full_prompt}],
                max_tokens=2000,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"GPT-4o call failed: {e}", exc_info=True)
            raise AIClientError(f"The AI service failed to process the request: {e}") from e

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def _call_gemini_flash(self, prompt: str, file_path: Optional[str] = None) -> str:
        """Call Gemini 1.5 Flash for heavy files and multimodal tasks."""
        self._ensure_gemini_initialized()
        full_prompt = create_safety_guard_prompt(prompt, "")
        
        try:
            model = genai.GenerativeModel(settings.SB_GEMINI_MODEL)
            logger.debug(f"Using Gemini 1.5 Flash (multimodal: {file_path is not None})")
            
            # Support multimodal if file_path provided
            if file_path and os.path.exists(file_path):
                # Upload file for multimodal processing
                uploaded_file = genai.upload_file(file_path)
                response = model.generate_content(
                    [full_prompt, uploaded_file],
                    request_options={"timeout": 60.0}
                )
            else:
                response = model.generate_content(
                    full_prompt,
                    request_options={"timeout": 45.0}
                )
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini Flash call failed: {e}", exc_info=True)
            raise AIClientError(f"The AI service failed to process the request: {e}") from e

    def _apply_baby_capy_prompt(self, prompt: str) -> str:
        """Modify prompt for Baby Capy mode - simple, friendly explanations."""
        baby_prefix = """
🍼 Baby Capy Mode Active! 🦫

You are Baby Avner - explain everything like you're talking to a 5-year-old child!

Your style:
- Use VERY simple words (like "big" instead of "significant")
- Make short sentences (5-10 words max per sentence)
- Use real-life examples that kids understand (like toys, food, family)
- Be warm, encouraging, and fun
- Use emojis to make it friendly
- Break complex ideas into tiny pieces

Example: Instead of "photosynthesis is the process by which plants convert light energy"
Say: "Plants are like solar panels! ☀️ They eat sunlight for breakfast. The sun gives them energy, just like your food gives you energy to play! 🌱"

Remember: Explain it so a 5-year-old would say "Oh! I get it now!"

Original request:
"""
        return baby_prefix + prompt

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def generate_text(self, prompt: str, context: str, task_type: TaskType = "standard",
                     require_json: bool = False, baby_mode: bool = False) -> str:
        """
        Generates text using smart routing to the optimal AI model.
        
        This method maintains backward compatibility with the old AIClient interface
        while leveraging the new routing capabilities.
        
        Args:
            prompt: The prompt to send to the AI
            context: Additional context (combined with prompt)
            task_type: Type of task for routing decision
            require_json: Whether to enforce JSON output
            baby_mode: Whether to use Baby Capy mode
            
        Returns:
            Generated text from the optimal AI model
        """
        # Combine prompt and context as before
        full_content = f"{prompt}\n\nContext:\n{context}" if context else prompt
        
        return self.route_task(
            task_type=task_type,
            content=full_content,
            require_json=require_json,
            baby_mode=baby_mode
        )


# Backward compatibility: AIClient is now TripleHybridClient
class AIClient(TripleHybridClient):
    """
    Backward compatible AIClient that uses TripleHybridClient under the hood.
    
    This ensures existing code continues to work while benefiting from
    the new smart routing capabilities.
    """
    pass


# Default client instance (lazy initialization)
ai_client = AIClient(provider=settings.SB_DEFAULT_PROVIDER)
