# validation_utils.py
"""
Lightweight validation utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


class ValidationError(ValueError):
    """Raised when validation fails."""


@dataclass
class ProcessDocumentRequest:
    user_id: str
    document_ids: List[str]

    def validate(self) -> None:
        if not self.user_id:
            raise ValidationError("user_id is required.")
        if not self.document_ids:
            raise ValidationError("At least one document_id is required.")


@dataclass
class AskQuestionRequest:
    user_id: str
    question: str
    document_ids: Optional[List[str]] = None  # None = whole workspace

    def validate(self) -> None:
        if not self.user_id:
            raise ValidationError("user_id is required.")
        if not self.question or not self.question.strip():
            raise ValidationError("question is required.")