from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

def _utc_now():
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)

class Document(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(..., alias="_id")
    filename: str
    content_text: str
    created_at: datetime = Field(default_factory=_utc_now)
    
    def to_dict(self):
        """Convert model to dictionary for MongoDB."""
        return self.model_dump(by_alias=True)

class Flashcard(BaseModel):
    question: str
    answer: str

class FlashcardSet(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(..., alias="_id")
    document_id: str
    cards: List[Flashcard]
    created_at: datetime = Field(default_factory=_utc_now)
    
    def to_dict(self):
        """Convert model to dictionary for MongoDB."""
        return self.model_dump(by_alias=True)

class AssessmentQuestion(BaseModel):
    question: str
    options: Optional[List[str]] = None
    correct_answer: str

class Assessment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(..., alias="_id")
    document_id: str
    questions: List[AssessmentQuestion]
    created_at: datetime = Field(default_factory=_utc_now)
    
    def to_dict(self):
        """Convert model to dictionary for MongoDB."""
        return self.model_dump(by_alias=True)

class Task(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(..., alias="_id")
    status: TaskStatus = TaskStatus.PENDING
    result_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    
    def to_dict(self):
        """Convert model to dictionary for MongoDB."""
        return self.model_dump(by_alias=True)
