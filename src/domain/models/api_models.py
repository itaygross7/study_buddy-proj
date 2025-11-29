from pydantic import BaseModel, Field
from typing import List, Optional

class BaseRequest(BaseModel):
    """Base model for API requests."""
    document_id: str = Field(..., description="The ID of the uploaded document to process.")
    user_id: Optional[str] = Field(None, description="Optional user identifier.")

class SummarizeRequest(BaseRequest):
    """Request model for the summarization endpoint."""
    pass

class FlashcardsRequest(BaseRequest):
    """Request model for the flashcards endpoint."""
    num_cards: int = Field(10, gt=0, le=50, description="Number of flashcards to generate.")

class AssessRequest(BaseRequest):
    """Request model for the assessment endpoint."""
    num_questions: int = Field(5, gt=0, le=25, description="Number of questions to generate.")
    question_type: str = Field("mcq", description="Type of questions (e.g., 'mcq', 'open').")

class HomeworkRequest(BaseModel):
    """Request model for the homework helper endpoint."""
    problem_statement: str = Field(..., description="The homework problem to be solved.")
    user_id: Optional[str] = Field(None, description="Optional user identifier.")

class TaskResponse(BaseModel):
    """Response model for endpoints that trigger async tasks."""
    task_id: str
    status: str
    polling_url: str
