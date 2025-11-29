from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Document(BaseModel):
    id: str = Field(..., alias="_id")
    filename: str
    content_text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Flashcard(BaseModel):
    question: str
    answer: str

class FlashcardSet(BaseModel):
    id: str = Field(..., alias="_id")
    document_id: str
    cards: List[Flashcard]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AssessmentQuestion(BaseModel):
    question: str
    options: Optional[List[str]] = None
    correct_answer: str

class Assessment(BaseModel):
    id: str = Field(..., alias="_id")
    document_id: str
    questions: List[AssessmentQuestion]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Task(BaseModel):
    id: str = Field(..., alias="_id")
    status: TaskStatus = TaskStatus.PENDING
    result_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
