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

class DocumentStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"

# --- Core Domain Objects ---

@dataclass
class Document:
    id: str
    user_id: str
    course_id: str
    filename: str
    content_text: str  # This will now store a status message, not full text
    status: DocumentStatus = DocumentStatus.UPLOADED
    gridfs_id: Optional[str] = None  # ADDED: Link to GridFS file
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class DocumentChunk:
    document_id: str
    chunk_index: int
    heading: str
    content: str
    # vector: Optional[List[float]] = None # For future semantic search

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
    user_id: str
    document_id: Optional[str] = None
    task_type: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    params: Dict = field(default_factory=dict)

@dataclass
class Job:
    """A dataclass to represent a job to be sent to the queue."""
    task_id: str
    document_id: str
    params: Dict = field(default_factory=dict)
