import os
from typing import Optional, Literal, Dict, Any

import google.generativeai as genai
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from src.infrastructure.config import settings
from sb_utils.logger_utils import logger
from sb_utils.ai_safety import create_safety_guard_prompt
from src.domain.errors import AIClientError
from src.services.avner_learning import continuous_improvement


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
    "standard",
]

# Tasks where teaching-style improvements make sense
TEACHING_TASK_TYPES: set[str] = {
    "summary",
    "homework",
    "assessment",
    "flashcards",
    "chat",        # Avner chat / tutoring-style answers
    "quiz",        # JSON quiz generation still benefits from better prompt
    "glossary",    # Explanatory, student-facing
}


class TripleHybridClient:
    def __init__(self, provider: str = None):
        self.provider = provider or settings.SB_DEFAULT_PROVIDER
        self._openai_initialized = False
        self._gemini_initialized = False

    # -------------------------------------------------------------------------
    # Provider init
    # -------------------------------------------------------------------------
    def _ensure_openai_initialized(self) -> None:
        if self._openai_initialized:
            return
        if not settings.OPENAI_API_KEY or "your_openai" in settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is not configured.")
        self._openai_initialized = True

    def _ensure_gemini_initialized(self) -> None:
        if self._gemini_initialized:
            return
        if not settings.GEMINI_API_KEY or "your_google" in settings.GEMINI_API_KEY:
            raise ValueError("Gemini API key is not configured.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._gemini_initialized = True

    # -------------------------------------------------------------------------
    # Routing
    # -------------------------------------------------------------------------
    def route_task(
        self,
        task_type: TaskType,
        content: str,
        file_path: Optional[str] = None,
        require_json: bool = False,
        baby_mode: bool = False,
    ) -> str:
        """
        Decide which model to call, based on task_type / flags.

        NOTE:
        - `content` must already be fully prepared:
          safety-wrapped + context + any continuous-improvement tweaks.
        """
        logger.debug(
            f"Routing task_type='{task_type}' require_json={require_json} baby_mode={baby_mode}"
        )

        # 1) Baby mode → OpenAI with baby style
        if baby_mode or task_type == "baby_capy":
            logger.info(f"→ Routing to {settings.SB_OPENAI_MODEL} (Baby Capy mode)")
            return self._call_gpt_mini(content, require_json=False, baby_mode=True)

        # 2) JSON-structured tasks → OpenAI
        if require_json or task_type in ["quiz", "assessment", "flashcards"]:
            logger.info(
                f"→ Routing to {settings.SB_OPENAI_MODEL} (JSON required for task_type={task_type})"
            )
            return self._call_gpt_mini(content, require_json=True)

        # 3) Chat-style tasks → OpenAI
        if task_type == "chat":
            logger.info(f"→ Routing to {settings.SB_OPENAI_MODEL} (task_type=chat)")
            return self._call_gpt_mini(content, require_json=False)

        # 4) Everything else → Gemini Flash
        logger.info(f"→ Routing to {settings.SB_GEMINI_MODEL} (task_type={task_type})")
        return self._call_gemini_flash(content, file_path)

    # -------------------------------------------------------------------------
    # OpenAI path
    # -------------------------------------------------------------------------
    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def _call_gpt_mini(
        self,
        prompt: str,
        require_json: bool = False,
        baby_mode: bool = False,
    ) -> str:
        """
        Call OpenAI chat model.

        IMPORTANT:
        - `prompt` is already safety-wrapped and context-grounded.
        - We do NOT call create_safety_guard_prompt here.
        """
        self._ensure_openai_initialized()

        # Baby Capy is applied as a light prefix to the already-wrapped prompt
        if baby_mode:
            prompt = self._apply_baby_capy_prompt(prompt)

        try:
            client_args: Dict[str, Any] = {
                "api_key": settings.OPENAI_API_KEY,
                "timeout": 30.0,
            }
            if getattr(settings, "SB_BASE_URL", None):
                client_args["base_url"] = settings.SB_BASE_URL

            client = openai.OpenAI(**client_args)

            messages = [{"role": "user", "content": prompt}]
            kwargs: Dict[str, Any] = {
                "model": settings.SB_OPENAI_MODEL,
                "messages": messages,
                "max_tokens": 1500,
                "temperature": 0.7,
            }

            if require_json:
                kwargs["response_format"] = {"type": "json_object"}
                if "json" not in prompt.lower():
                    kwargs["messages"][0]["content"] = (
                        prompt + "\nReturn your response as valid JSON."
                    )

            logger.debug(
                f"Using {settings.SB_OPENAI_MODEL} (JSON: {require_json}, Baby: {baby_mode})"
            )
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"{settings.SB_OPENAI_MODEL} call failed: {e}", exc_info=True)
            raise AIClientError(
                f"The AI service failed to process the request: {e}"
            ) from e

    # -------------------------------------------------------------------------
    # Gemini path
    # -------------------------------------------------------------------------
    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def _call_gemini_flash(
        self,
        prompt: str,
        file_path: Optional[str] = None,
    ) -> str:
        """
        Call Gemini Flash (optionally with an uploaded file).

        IMPORTANT:
        - `prompt` is already safety-wrapped and context-grounded.
        """
        self._ensure_gemini_initialized()

        try:
            model = genai.GenerativeModel(settings.SB_GEMINI_MODEL)
            logger.debug(
                f"Using {settings.SB_GEMINI_MODEL} (multimodal: {file_path is not None})"
            )

            if file_path and os.path.exists(file_path):
                uploaded_file = genai.upload_file(file_path)
                response = model.generate_content(
                    [prompt, uploaded_file],
                    request_options={"timeout": 60.0},
                )
            else:
                response = model.generate_content(
                    prompt,
                    request_options={"timeout": 45.0},
                )

            return (response.text or "").strip()

        except Exception as e:
            logger.error(f"Gemini Flash call failed: {e}", exc_info=True)
            raise AIClientError(
                f"The AI service failed to process the request: {e}"
            ) from e

    # -------------------------------------------------------------------------
    # Styles
    # -------------------------------------------------------------------------
    def _apply_baby_capy_prompt(self, prompt: str) -> str:
        """
        Apply the Baby Capy style on top of the already-guarded prompt.
        """
        baby_prefix = (
            "🍼 Baby Capy Mode Active! 🦫 "
            "Explain everything like you're talking to a 5-year-old child. "
            "Use super simple words, short sentences, and a cute, friendly tone.\n\n"
        )
        return baby_prefix + prompt

    # -------------------------------------------------------------------------
    # Main public entrypoint
    # -------------------------------------------------------------------------
    def generate_text(
        self,
        prompt: str,
        context: str,
        task_type: TaskType = "standard",
        *,
        require_json: bool = False,
        baby_mode: bool = False,
        user_id: Optional[str] = None,
        user_prefs: Optional[Dict[str, Any]] = None,
        use_learning: bool = True,
    ) -> str:
        """
        Main high-level API used across the app.

        - `prompt`: base task description (e.g. "Summarize...", "Create quiz...").
        - `context`: the student's material / RAG context.
        - `task_type`: semantic type of the task.
        - `require_json`: enforce JSON for quiz/assessment/flashcards.
        - `baby_mode`: Baby Avner explanation style.
        - `user_id` / `user_prefs`: used by the continuous-improvement engine.
        - `use_learning`: if False, skip all learning-based prompt tweaks.
        """
        effective_prompt = prompt

        # 1) Teaching-style enhancement (only where it makes sense)
        try:
            should_improve = (
                use_learning
                and user_id is not None
                and user_prefs is not None
                and task_type in TEACHING_TASK_TYPES
            )

            if should_improve:
                effective_prompt = continuous_improvement.enhance_prompt_with_learnings(
                    base_prompt=prompt,
                    user_id=user_id,
                    task_type=task_type,
                    user_prefs=user_prefs,
                )
        except Exception as e:
            # Never break user flow because of the learning layer
            logger.error(
                f"Prompt improvement failed, falling back to base prompt: {e}",
                exc_info=True,
            )
            effective_prompt = prompt

        # 2) Safety + context grounding (single source of truth)
        safe_full_prompt = create_safety_guard_prompt(
            prompt=effective_prompt,
            context=context or "",
        )

        # 3) Route to the right provider
        return self.route_task(
            task_type=task_type,
            content=safe_full_prompt,
            require_json=require_json,
            baby_mode=baby_mode,
        )


class AIClient(TripleHybridClient):
    """Concrete client used by the rest of the app."""
    pass


ai_client = AIClient(provider=settings.SB_DEFAULT_PROVIDER)
