# models_utils.py
"""
Core shared models, configs, and error types.

Generic enough for any backend, but tuned for an AI + queue + Mongo stack.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


# =========================
# Error hierarchy
# =========================

class InfraError(RuntimeError):
    """Base error for infra-related failures."""


class RabbitError(InfraError):
    """RabbitMQ related error."""


class MongoError(InfraError):
    """MongoDB related error."""


class CeleryInfraError(InfraError):
    """Celery / task infra related error."""


class LLMError(InfraError):
    """LLM related error."""


class FileInfraError(InfraError):
    """File-system / storage related error."""


# =========================
# Infra configs
# =========================

@dataclass(frozen=True)
class RabbitConfig:
    """
    Configuration for RabbitMQ usage.

    url: AMQP URL, e.g. amqp://user:pass@host:5672/vhost
    """
    url: str
    default_exchange: str = ""
    default_routing_key: str = "studybuddy"
    prefetch_count: int = 10
    heartbeat: int = 60
    connection_attempts: int = 3
    retry_delay_seconds: int = 3


@dataclass(frozen=True)
class MongoConfig:
    """
    Configuration for MongoDB.
    """
    uri: str
    database: str
    # Optional mapping from logical names to collection names
    collections: Dict[str, str] = field(default_factory=dict)
    connect_timeout_ms: int = 10_000


@dataclass(frozen=True)
class CeleryConfig:
    """
    Configuration for Celery application.
    """
    broker_url: str
    result_backend: str
    default_queue: str = "default"
    task_soft_time_limit: int = 60  # seconds
    task_time_limit: int = 90       # hard kill


# =========================
# LLM model configs
# =========================

class LLMProvider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"   # Gemini support


class ModelPurpose(str, Enum):
    """
    High-level usage categories to help pick the right model.
    """
    CHAT_LIGHT = "chat_light"            # short, cheap interactions
    CHAT_DEEP = "chat_deep"              # longer, multi-step reasoning
    RAG_QUERY = "rag_query"              # answer using indexed docs
    RAG_INDEX_BUILD = "rag_index_build"  # summarization / indexing
    TOOLING = "tooling"                  # code, scripts, dev tasks


@dataclass(frozen=True)
class ModelConfig:
    """
    Metadata for a single LLM model allowed in the system.
    """
    name: str
    provider: LLMProvider
    max_input_tokens: int
    max_output_tokens: int
    relative_cost: float = 1.0  # 1.0 = baseline, >1 more expensive, <1 cheaper
    recommended_purposes: List[ModelPurpose] = field(default_factory=list)
    is_default: bool = False


@dataclass
class LLMSelectorConfig:
    """
    Configuration for LLM model selection.

    - available_models: all models the system is allowed to use.
    - selector_model_name: model used to *decide* which model to use
      (usually a cheap mini model).
    - enable_ai_selector: if True, try LLM-based selector first, otherwise use heuristics.
    """
    available_models: List[ModelConfig]
    selector_model_name: str
    enable_ai_selector: bool = True
    small_input_chars: int = 2_000
    medium_input_chars: int = 16_000

    def get_default_model(self) -> ModelConfig:
        for m in self.available_models:
            if m.is_default:
                return m
        if not self.available_models:
            raise LLMError("No available LLM models configured.")
        return self.available_models[0]

    def find_model_by_name(self, name: str) -> ModelConfig:
        for m in self.available_models:
            if m.name == name:
                return m
        raise LLMError(f"Requested model '{name}' is not in available_models.")

    def candidates_for_purpose(self, purpose: ModelPurpose) -> List[ModelConfig]:
        candidates = [
            m
            for m in self.available_models
            if not m.recommended_purposes or purpose in m.recommended_purposes
        ]
        return candidates or self.available_models