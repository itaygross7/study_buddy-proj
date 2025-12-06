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
    "heavy_file",      # Gemini: Audio, video, large PDFs
    "summary",         # Gemini: Text summarization
    "homework",        # Gemini: Problem solving & explanations
    "diagram",         # Gemini: Mermaid diagrams, visual generation
    "glossary",        # Gemini: Term extraction
    "quiz",            # OpenAI: Quiz generation (JSON required)
    "assessment",      # OpenAI: Assessment questions (JSON required)
    "flashcards",      # OpenAI: Flashcard generation (JSON required)
    "baby_capy",       # OpenAI: Simplified explanations
    "chat",            # OpenAI: Conversational responses
    "standard"         # Fallback to default provider
]


class TripleHybridClient:
    """
    Triple Hybrid AI Client - Intelligent routing to optimal model for each task.
    
    ROUTING RULES (Balanced 50/50 Distribution):
    
    === GEMINI FLASH (Cost-effective, multimodal, fast) ===
    1. Heavy file processing (audio, video, large PDFs) - task_type="heavy_file"
    2. Text summarization - task_type="summary"
    3. Homework solutions & explanations - task_type="homework"
    4. Diagram generation (Mermaid, etc.) - task_type="diagram"
    5. Standard/unspecified tasks - task_type="standard"
    
    === GPT-4o-MINI (JSON enforcement, chat, structured output) ===
    6. Quiz generation (requires JSON) - task_type="quiz" or require_json=True
    7. Assessment questions (requires JSON) - task_type="assessment" or require_json=True
    8. Flashcard generation (requires JSON) - task_type="flashcards" or require_json=True
    9. Glossary/term extraction (requires JSON) - task_type="glossary" with require_json=True
    10. Chat/conversational (Avner) - task_type="chat"
    11. Baby Capy mode (simple explanations) - task_type="baby_capy" or baby_mode=True
    
    ROUTING PRIORITY:
    1. baby_mode=True → OpenAI (override everything)
    2. require_json=True → OpenAI (JSON enforcement needed)
    3. task_type → Route to designated provider
    4. default → Gemini Flash
    
    This ensures balanced distribution while leveraging each model's strengths:
    - Gemini: Multimodal, summarization, explanations, cost-effective text
    - OpenAI: JSON output, chat, structured data, simplified teaching
    
    Model selection is configurable via environment variables:
    - SB_OPENAI_MODEL: OpenAI model to use (default: gpt-4o-mini)
    - SB_GEMINI_MODEL: Gemini model to use (default: gemini-1.5-flash-latest)
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
        Intelligent router that selects the optimal model based on explicit rules.
        
        ROUTING LOGIC:
        - Gemini Flash: heavy_file, summary, homework, diagram, glossary
        - GPT-4o-mini: quiz, assessment, flashcards, baby_capy, chat, JSON-required tasks
        
        Args:
            task_type: Type of task to perform (determines model selection)
            content: The content/prompt to process
            file_path: Optional file path for multimodal tasks
            require_json: Whether to enforce JSON output (routes to OpenAI)
            baby_mode: Whether to use Baby Capy simplified explanations (routes to OpenAI)
            
        Returns:
            Generated text from the selected AI model
        """
        # Log routing decision for monitoring
        logger.debug(f"Routing task_type='{task_type}' require_json={require_json} baby_mode={baby_mode}")
        
        # === OPENAI ROUTES ===
        # Baby Capy mode always uses OpenAI for consistent simple explanations
        if baby_mode or task_type == "baby_capy":
            logger.info(f"→ Routing to GPT-4o-mini (Baby Capy mode)")
            return self._call_gpt_mini(content, require_json=False, baby_mode=True)
        
        # JSON-required tasks must use OpenAI (Gemini doesn't enforce JSON)
        if require_json:
            logger.info(f"→ Routing to GPT-4o-mini (JSON required)")
            return self._call_gpt_mini(content, require_json=True)
        
        # Quiz, Assessment, Flashcards (JSON output needed)
        if task_type in ["quiz", "assessment", "flashcards"]:
            logger.info(f"→ Routing to GPT-4o-mini (task_type={task_type})")
            return self._call_gpt_mini(content, require_json=True)
        
        # Chat/conversational (Avner chatbot)
        if task_type == "chat":
            logger.info(f"→ Routing to GPT-4o-mini (task_type=chat)")
            return self._call_gpt_mini(content, require_json=False)
        
        # === GEMINI ROUTES ===
        # Heavy files with multimodal support
        if task_type == "heavy_file":
            logger.info(f"→ Routing to Gemini Flash (task_type=heavy_file, multimodal={file_path is not None})")
            return self._call_gemini_flash(content, file_path)
        
        # Text summarization
        if task_type == "summary":
            logger.info(f"→ Routing to Gemini Flash (task_type=summary)")
            return self._call_gemini_flash(content, file_path)
        
        # Homework solutions & explanations
        if task_type == "homework":
            logger.info(f"→ Routing to Gemini Flash (task_type=homework)")
            return self._call_gemini_flash(content, file_path)
        
        # Diagram generation (Mermaid, etc.)
        if task_type == "diagram":
            logger.info(f"→ Routing to Gemini Flash (task_type=diagram)")
            return self._call_gemini_flash(content, file_path)
        
        # === DEFAULT ROUTE ===
        # Standard/unspecified tasks use default provider (Gemini per config)
        logger.info(f"→ Routing to Gemini Flash (task_type=standard/default)")
        return self._call_gemini_flash(content, file_path)

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
                "model": settings.SB_OPENAI_MODEL,
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
            
            logger.debug(f"Using {settings.SB_OPENAI_MODEL} (JSON mode: {require_json}, Baby mode: {baby_mode})")
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
            
            logger.debug(f"Using {settings.SB_OPENAI_MODEL} for complex reasoning")
            response = client.chat.completions.create(
                model=settings.SB_OPENAI_MODEL,
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
