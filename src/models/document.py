from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Document(BaseModel):
    """
    Represents a document uploaded by a user.
    """
    id: Optional[str] = Field(alias="_id")
    user_id: str
    filename: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
