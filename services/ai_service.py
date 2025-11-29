from typing import Any, Dict, Optional
import time
import logging
import random

logger = logging.getLogger(__name__)

class AIService:
    """
    Wrapper for LLM calls. Retries with exponential backoff, timeout per-call.
    Important: DO NOT log user content or API keys.
    """

    def __init__(self, client: Any, timeout_s: int = 20, retries: int = 2):
        self.client = client  # injected LLM client wrapper
        self.timeout_s = timeout_s
        self.retries = retries

    def call(self, prompt: str, params: Optional[Dict] = None) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("empty_prompt")
        params = params or {}
        attempt = 0
        while True:
            try:
                attempt += 1
                # call must honor timeout - client implementation should support it
                response = self.client.generate(prompt=prompt, timeout=self.timeout_s, **params)
                # response must be sanitized by client
                return response
            except Exception as exc:
                logger.debug("AI call failed attempt %d: %s", attempt, type(exc).__name__)
                if attempt > self.retries:
                    logger.warning("AI service unavailable after %d attempts", attempt)
                    raise
                # backoff with jitter
                backoff = (2 ** attempt) + random.random()
                time.sleep(backoff)

