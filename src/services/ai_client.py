import google.generativeai as genai
import openai
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional, Literal
import os

from src.infrastructure.config import settings
from sb_utils.logger_utils import logger
from sb_utils.ai_safety import create_safety_guard_prompt
from src.domain.errors import AIClientError


TaskType = Literal[
    "heavy_file",
    "summary",
    "homework",
    "diagram",
    "glossary",
    "quiz",
    "assessment",
    "flashcards",
    "baby_capy",
    "chat",
    "standard"
]


class TripleHybridClient:
    def __init__(self, provider: str = None):
        self.provider = provider or settings.SB_DEFAULT_PROVIDER
        self._openai_initialized = False
        self._gemini_initialized = False

    def _ensure_openai_initialized(self):
        if self._openai_initialized: return
        if not settings.OPENAI_API_KEY or "your_openai" in settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is not configured.")
        self._openai_initialized = True

    def _ensure_gemini_initialized(self):
        if self._gemini_initialized: return
        if not settings.GEMINI_API_KEY or "your_google" in settings.GEMINI_API_KEY:
            raise ValueError("Gemini API key is not configured.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._gemini_initialized = True

    def route_task(self, task_type: TaskType, content: str, file_path: Optional[str] = None,
                   require_json: bool = False, baby_mode: bool = False) -> str:
        logger.debug(f"Routing task_type='{task_type}' require_json={require_json} baby_mode={baby_mode}")
        
        if baby_mode or task_type == "baby_capy":
            logger.info(f"→ Routing to {settings.SB_OPENAI_MODEL} (Baby Capy mode)")
            return self._call_gpt_mini(content, require_json=False, baby_mode=True)
        
        if require_json or task_type in ["quiz", "assessment", "flashcards"]:
            logger.info(f"→ Routing to {settings.SB_OPENAI_MODEL} (JSON required for task_type={task_type})")
            return self._call_gpt_mini(content, require_json=True)
        
        if task_type == "chat":
            logger.info(f"→ Routing to {settings.SB_OPENAI_MODEL} (task_type=chat)")
            return self._call_gpt_mini(content, require_json=False)
        
        logger.info(f"→ Routing to {settings.SB_GEMINI_MODEL} (task_type={task_type})")
        return self._call_gemini_flash(content, file_path)

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def _call_gpt_mini(self, prompt: str, require_json: bool = False, baby_mode: bool = False) -> str:
        self._ensure_openai_initialized()
        if baby_mode: prompt = self._apply_baby_capy_prompt(prompt)
        full_prompt = create_safety_guard_prompt(prompt, "")
        
        try:
            # --- THIS IS THE FIX ---
            # Only pass base_url if it's actually set.
            client_args = {"api_key": settings.OPENAI_API_KEY, "timeout": 30.0}
            if settings.SB_BASE_URL:
                client_args["base_url"] = settings.SB_BASE_URL
            client = openai.OpenAI(**client_args)
            # --- END OF FIX ---

            kwargs = {"model": settings.SB_OPENAI_MODEL, "messages": [{"role": "user", "content": full_prompt}], "max_tokens": 1500, "temperature": 0.7}
            if require_json:
                kwargs["response_format"] = {"type": "json_object"}
                if "json" not in full_prompt.lower():
                    kwargs["messages"][0]["content"] = full_prompt + "\nReturn your response as valid JSON."
            
            logger.debug(f"Using {settings.SB_OPENAI_MODEL} (JSON: {require_json}, Baby: {baby_mode})")
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"{settings.SB_OPENAI_MODEL} call failed: {e}", exc_info=True)
            raise AIClientError(f"The AI service failed to process the request: {e}") from e

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def _call_gemini_flash(self, prompt: str, file_path: Optional[str] = None) -> str:
        self._ensure_gemini_initialized()
        full_prompt = create_safety_guard_prompt(prompt, "")
        
        try:
            model = genai.GenerativeModel(settings.SB_GEMINI_MODEL)
            logger.debug(f"Using {settings.SB_GEMINI_MODEL} (multimodal: {file_path is not None})")
            
            if file_path and os.path.exists(file_path):
                uploaded_file = genai.upload_file(file_path)
                response = model.generate_content([full_prompt, uploaded_file], request_options={"timeout": 60.0})
            else:
                response = model.generate_content(full_prompt, request_options={"timeout": 45.0})
            
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini Flash call failed: {e}", exc_info=True)
            raise AIClientError(f"The AI service failed to process the request: {e}") from e

    def _apply_baby_capy_prompt(self, prompt: str) -> str:
        baby_prefix = "🍼 Baby Capy Mode Active! 🦫 Explain everything like you're talking to a 5-year-old child..."
        return baby_prefix + prompt

    def generate_text(self, prompt: str, context: str, task_type: TaskType = "standard",
                     require_json: bool = False, baby_mode: bool = False) -> str:
        full_content = f"{prompt}\n\nContext:\n{context}" if context else prompt
        return self.route_task(task_type=task_type, content=full_content, require_json=require_json, baby_mode=baby_mode)

class AIClient(TripleHybridClient):
    pass

ai_client = AIClient(provider=settings.SB_DEFAULT_PROVIDER)
