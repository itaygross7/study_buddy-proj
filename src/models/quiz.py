from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Question(BaseModel):
    """
    Represents a single question in a quiz.
    """
    question: str
    options: List[str]
    answer: str


class Quiz(BaseModel):
    """
    Represents a quiz created by the Assess-Me tool.
    """
    id: Optional[str] = Field(alias="_id")
    user_id: str
    title: str
    questions: List[Question]
    created_at: datetime = Field(default_factory=datetime.utcnow)
