from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict

# --- Enums ---


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AIProvider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"

# --- Core Domain Objects ---


@dataclass
class Document:
    id: str
    filename: str
    content_text: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Flashcard:
    question: str
    answer: str


@dataclass
class FlashcardSet:
    id: str
    document_id: str
    cards: List[Flashcard]
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Summary:
    id: str
    document_id: str
    summary_text: str
    follow_up_questions: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)

# --- Task & Job Models ---


@dataclass
class Task:
    id: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict] = None  # Can store final result data
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Job:
    """A dataclass to represent a job to be sent to the queue."""
    task_id: str
    document_id: str
    # Add other job-specific params here
    params: Dict = field(default_factory=dict)
