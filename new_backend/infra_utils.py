# infra_utils.py
"""
Infra handlers.

- RabbitHandler: message queue operations
- MongoHandler: DB operations
- CeleryHandler: background task orchestration
- LLMHandler: all communication with LLMs (OpenAI + Gemini, with model selection)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

import openai
import pymongo
from celery import Celery
from pika import BlockingConnection, URLParameters
from pika.adapters.blocking_connection import BlockingChannel
from tenacity import (
    retry,
    wait_exponential_jitter,
    stop_after_attempt,
    retry_if_exception_type,
)

# Gemini is optional
try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover
    genai = None  # type: ignore

from models_utils import (
    RabbitConfig,
    MongoConfig,
    CeleryConfig,
    LLMSelectorConfig,
    ModelConfig,
    ModelPurpose,
    LLMProvider,
    RabbitError,
    MongoError,
    CeleryInfraError,
    LLMError,
)

logger = logging.getLogger("studybuddy.infra")

ChatMessage = Dict[str, str]  # {"role": "user" | "system" | "assistant", "content": "..."}


# =========================
# RabbitHandler
# =========================

@dataclass
class RabbitHandler:
    config: RabbitConfig
    _connection: Optional[BlockingConnection] = None
    _channel: Optional[BlockingChannel] = None

    def _ensure_channel(self) -> BlockingChannel:
        if self._channel and self._channel.is_open:
            return self._channel

        logger.info(
            "Opening RabbitMQ connection",
            extra={"url_preview": self._safe_url_preview(self.config.url)},
        )
        try:
            params = URLParameters(self.config.url)
            self._connection = BlockingConnection(params)
            self._channel = self._connection.channel()
            self._channel.basic_qos(prefetch_count=self.config.prefetch_count)
            return self._channel
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to open RabbitMQ connection")
            raise RabbitError(str(exc)) from exc

    @staticmethod
    def _safe_url_preview(url: str) -> str:
        if "@" in url:
            return url.split("@", 1)[-1]
        return url

    @retry(
        wait=wait_exponential_jitter(initial=0.5, max=5),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(RabbitError),
        reraise=True,
    )
    def publish(
        self,
        body: Dict[str, Any],
        *,
        routing_key: Optional[str] = None,
        exchange: Optional[str] = None,
    ) -> None:
        ch = self._ensure_channel()
        body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        rk = routing_key or self.config.default_routing_key
        ex = exchange or self.config.default_exchange

        logger.debug(
            "RabbitHandler.publish",
            extra={"exchange": ex, "routing_key": rk, "body_preview": str(body)[:200]},
        )

        try:
            ch.basic_publish(exchange=ex, routing_key=rk, body=body_bytes)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to publish RabbitMQ message")
            raise RabbitError(str(exc)) from exc

    def close(self) -> None:
        try:
            if self._channel and self._channel.is_open:
                self._channel.close()
            if self._connection and self._connection.is_open:
                self._connection.close()
        except Exception:
            logger.debug("Error while closing RabbitMQ connection", exc_info=True)


# =========================
# MongoHandler
# =========================

@dataclass
class MongoHandler:
    config: MongoConfig
    _client: Optional[pymongo.MongoClient] = None

    def _ensure_client(self) -> pymongo.MongoClient:
        if self._client:
            return self._client

        logger.info(
            "Connecting to MongoDB",
            extra={"uri_preview": self._safe_uri_preview(self.config.uri)},
        )
        try:
            self._client = pymongo.MongoClient(
                self.config.uri,
                serverSelectionTimeoutMS=self.config.connect_timeout_ms,
            )
            self._client.admin.command("ping")
            return self._client
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to connect to MongoDB")
            raise MongoError(str(exc)) from exc

    @staticmethod
    def _safe_uri_preview(uri: str) -> str:
        if "@" in uri:
            return uri.split("@", 1)[-1]
        return uri

    @property
    def db(self) -> pymongo.database.Database:
        return self._ensure_client()[self.config.database]

    def collection(self, logical_name: str) -> pymongo.collection.Collection:
        actual = self.config.collections.get(logical_name, logical_name)
        return self.db[actual]

    def insert_one(self, logical_collection: str, doc: Dict[str, Any]) -> Any:
        col = self.collection(logical_collection)
        result = col.insert_one(doc)
        return result.inserted_id

    def find_one(self, logical_collection: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        col = self.collection(logical_collection)
        return col.find_one(query)

    def update_one(
        self,
        logical_collection: str,
        query: Dict[str, Any],
        update: Dict[str, Any],
        *,
        upsert: bool = False,
    ) -> None:
        col = self.collection(logical_collection)
        col.update_one(query, update, upsert=upsert)


# =========================
# CeleryHandler
# =========================

@dataclass
class CeleryHandler:
    config: CeleryConfig
    app: Celery

    @classmethod
    def from_config(cls, config: CeleryConfig) -> "CeleryHandler":
        app = Celery("studybuddy", broker=config.broker_url, backend=config.result_backend)
        app.conf.task_default_queue = config.default_queue
        app.conf.task_soft_time_limit = config.task_soft_time_limit
        app.conf.task_time_limit = config.task_time_limit
        return cls(config=config, app=app)

    def enqueue_task(self, task_name: str, *args: Any, **kwargs: Any) -> str:
        try:
            result = self.app.send_task(task_name, args=args, kwargs=kwargs)
            logger.info(
                "CeleryHandler.enqueue_task",
                extra={"task_name": task_name, "task_id": result.id},
            )
            return result.id
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to enqueue Celery task")
            raise CeleryInfraError(str(exc)) from exc

    def get_task_status(self, task_id: str) -> str:
        try:
            async_result = self.app.AsyncResult(task_id)
            return async_result.status
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to get Celery task status", extra={"task_id": task_id})
            raise CeleryInfraError(str(exc)) from exc

    def get_task_result(self, task_id: str) -> Any:
        try:
            async_result = self.app.AsyncResult(task_id)
            if async_result.failed():
                raise CeleryInfraError(f"Task {task_id} failed: {async_result.result}")
            return async_result.result
        except CeleryInfraError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to get Celery task result", extra={"task_id": task_id})
            raise CeleryInfraError(str(exc)) from exc


# =========================
# LLMHandler (OpenAI + Gemini)
# =========================

class LLMHandler:
    """
    Central gateway for all LLM communication.

    - Supports both OpenAI and Gemini, decided per-model.
    - Can use a "selector" model (OpenAI or Gemini) to choose the final model.
    - Has retry logic and safe logging.
    """

    def __init__(
        self,
        selector_config: LLMSelectorConfig,
        openai_client: Optional[openai.Client] = None,
        gemini_api_key: Optional[str] = None,
    ) -> None:
        self.selector_config = selector_config
        self._openai = openai_client or openai.Client()
        self._gemini_api_key = gemini_api_key

        if genai is not None and self._gemini_api_key:
            genai.configure(api_key=self._gemini_api_key)

    # ---------- public API ----------

    def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        purpose: ModelPurpose = ModelPurpose.CHAT_DEEP,
        require_reasoning: bool = False,
        input_text_preview: Optional[str] = None,
        force_model_name: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.2,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Main entry point for non-streaming LLM chat.

        - Selects model (OpenAI or Gemini) unless force_model_name is given.
        - Calls provider with retries.
        - Returns text content.
        """
        meta = metadata or {}
        input_chars = sum(len(m.get("content", "")) for m in messages)

        selected_model = (
            self._choose_model(
                purpose=purpose,
                input_chars=input_chars,
                require_reasoning=require_reasoning,
            )
            if force_model_name is None
            else self.selector_config.find_model_by_name(force_model_name)
        )

        preview = input_text_preview or self._build_input_preview(messages)

        logger.debug(
            "LLMHandler.chat.start",
            extra={
                "selected_model": selected_model.name,
                "provider": selected_model.provider.value,
                "purpose": purpose.value,
                "input_chars": input_chars,
                "metadata": meta,
                "input_preview": preview[:200],
            },
        )

        try:
            content = self._call_llm_with_retry(
                provider=selected_model.provider,
                model_name=selected_model.name,
                messages=messages,
                max_tokens=max_tokens or selected_model.max_output_tokens,
                temperature=temperature,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "LLMHandler.chat.failed",
                extra={
                    "selected_model": selected_model.name,
                    "provider": selected_model.provider.value,
                    "purpose": purpose.value,
                    "metadata": meta,
                },
            )
            raise LLMError(str(exc)) from exc

        logger.info(
            "LLMHandler.chat.done",
            extra={
                "selected_model": selected_model.name,
                "provider": selected_model.provider.value,
                "purpose": purpose.value,
                "metadata": meta,
                "output_preview": content[:200],
            },
        )
        return content

    # ---------- low-level call with retry ----------

    @retry(
        wait=wait_exponential_jitter(initial=0.5, max=5.0),
        stop=stop_after_attempt(4),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _call_llm_with_retry(
        self,
        *,
        provider: LLMProvider,
        model_name: str,
        messages: Sequence[ChatMessage],
        max_tokens: int,
        temperature: float,
    ) -> str:
        if provider is LLMProvider.OPENAI:
            resp = self._openai.chat.completions.create(
                model=model_name,
                messages=list(messages),
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=40,
            )
            return (resp.choices[0].message.content or "").strip()

        if provider is LLMProvider.GEMINI:
            if genai is None:
                raise LLMError(
                    "google-generativeai is not installed but a Gemini model was requested."
                )
            if not self._gemini_api_key:
                raise LLMError("Gemini API key not configured.")
            prompt = self._messages_to_prompt(messages)
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            return (getattr(resp, "text", "") or "").strip()

        raise LLMError(f"Unsupported provider: {provider.value}")

    # ---------- model selection ----------

    def _choose_model(
        self,
        *,
        purpose: ModelPurpose,
        input_chars: int,
        require_reasoning: bool,
    ) -> ModelConfig:
        if self.selector_config.enable_ai_selector:
            try:
                return self._choose_model_via_ai(
                    purpose=purpose,
                    input_chars=input_chars,
                    require_reasoning=require_reasoning,
                )
            except Exception:
                logger.warning(
                    "AI-based model selection failed; falling back to heuristic."
                )

        return self._choose_model_heuristic(
            purpose=purpose,
            input_chars=input_chars,
            require_reasoning=require_reasoning,
        )

    def _choose_model_heuristic(
        self,
        *,
        purpose: ModelPurpose,
        input_chars: int,
        require_reasoning: bool,
    ) -> ModelConfig:
        candidates = self.selector_config.candidates_for_purpose(purpose)
        small_threshold = self.selector_config.small_input_chars
        medium_threshold = self.selector_config.medium_input_chars

        if input_chars <= small_threshold and not require_reasoning:
            return min(candidates, key=lambda m: m.relative_cost)

        if input_chars <= medium_threshold and not require_reasoning:
            sorted_by_cost = sorted(candidates, key=lambda m: m.relative_cost)
            mid_index = len(sorted_by_cost) // 2
            return sorted_by_cost[mid_index]

        return max(candidates, key=lambda m: m.relative_cost)

    def _choose_model_via_ai(
        self,
        *,
        purpose: ModelPurpose,
        input_chars: int,
        require_reasoning: bool,
    ) -> ModelConfig:
        selector_name = self.selector_config.selector_model_name
        selector_model = self.selector_config.find_model_by_name(selector_name)
        allowed_models = self.selector_config.available_models

        system_prompt = (
            "You are a routing assistant that chooses the best LLM model "
            "for a task based on input size, purpose, and cost."
        )
        models_description = [
            {
                "name": m.name,
                "provider": m.provider.value,
                "max_input_tokens": m.max_input_tokens,
                "max_output_tokens": m.max_output_tokens,
                "relative_cost": m.relative_cost,
                "purposes": [p.value for p in m.recommended_purposes] or ["any"],
            }
            for m in allowed_models
        ]

        user_prompt = (
            "You must choose exactly one model from the list below.\n\n"
            f"Task purpose: {purpose.value}\n"
            f"Input length (chars): {input_chars}\n"
            f"Require reasoning: {require_reasoning}\n\n"
            "Available models (JSON):\n"
            f"{json.dumps(models_description, ensure_ascii=False)}\n\n"
            "Rules:\n"
            "- Prefer cheaper models when they are sufficient.\n"
            "- For long inputs or complex reasoning, choose more powerful models.\n"
            "- Respond with ONLY the model 'name' string, nothing else.\n"
        )

        logger.debug(
            "LLMHandler._choose_model_via_ai.start",
            extra={
                "selector_model_name": selector_name,
                "provider": selector_model.provider.value,
                "purpose": purpose.value,
                "input_chars": input_chars,
                "require_reasoning": require_reasoning,
            },
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        content = self._call_llm_with_retry(
            provider=selector_model.provider,
            model_name=selector_model.name,
            messages=messages,
            max_tokens=20,
            temperature=0.0,
        )

        logger.info(
            "LLMHandler._choose_model_via_ai.chosen",
            extra={"selector_model_name": selector_name, "chosen": content[:100]},
        )

        return self.selector_config.find_model_by_name(content.strip())

    # ---------- helpers ----------

    @staticmethod
    def _build_input_preview(messages: Sequence[ChatMessage]) -> str:
        for m in reversed(messages):
            if m.get("role") == "user":
                return m.get("content", "")
        return messages[-1].get("content", "") if messages else ""

    @staticmethod
    def _messages_to_prompt(messages: Sequence[ChatMessage]) -> str:
        """
        Simple conversion of OpenAI-style messages → single prompt string
        for Gemini.
        """
        lines: list[str] = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            lines.append(f"{role.upper()}: {content}")
        return "\n".join(lines)