from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
from datetime import datetime, timezone
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

# --- THIS IS THE FIX ---
class DocumentStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
# --- END OF FIX ---

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class Language(str, Enum):
    HEBREW = "he"
    ENGLISH = "en"


def _utc_now():
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class UserProfile(BaseModel):
    """Extended user profile with personal and student info."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="_id")  # Same as user_id
    # Personal Info
    full_name: str = ""
    phone: str = ""
    # Student Info
    institution: str = ""  # University/College/School name
    degree: str = ""  # e.g., "B.Sc Computer Science"
    year_of_study: str = ""  # e.g., "2nd year", "3rd semester"
    # General context for AI - info that applies to all courses
    general_context: str = ""  # e.g., "I learn best with examples", "Prefer visual explanations"
    preferred_language: Language = Language.HEBREW
    updated_at: datetime = Field(default_factory=_utc_now)

    def to_dict(self):
        """Convert model to dictionary for MongoDB."""
        return self.model_dump(by_alias=True)


class Course(BaseModel):
    """A course/subject in user's library."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="_id")
    user_id: str  # Owner of this course
    name: str  # e.g., "Introduction to Psychology"
    description: str = ""  # Optional course description
    language: Language = Language.HEBREW  # Language for AI responses
    icon: str = "📚"  # Emoji icon for the course
    color: str = "#F2C94C"  # Color theme for the course
    # Stats
    document_count: int = 0
    summary_count: int = 0
    flashcard_count: int = 0
    assessment_count: int = 0
    # Timestamps
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    def to_dict(self):
        """Convert model to dictionary for MongoDB."""
        return self.model_dump(by_alias=True)

    def has_content(self) -> bool:
        """Check if course has any uploaded content."""
        return self.document_count > 0


class User(BaseModel):
    """User model for authentication."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="_id")
    email: str
    password_hash: str
    name: str = ""
    role: UserRole = UserRole.USER
    is_verified: bool = False
    verification_token: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)
    last_login: Optional[datetime] = None
    prompt_count: int = 0  # Track daily usage
    prompt_count_date: Optional[str] = None  # Date of last prompt count reset
    is_active: bool = True

    def to_dict(self):
        """Convert model to dictionary for MongoDB."""
        return self.model_dump(by_alias=True)

    def get_id(self):
        """Return the user id as a string for Flask-Login."""
        return self.id


class Document(BaseModel):
    """A document/material in a user's course library."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="_id")
    user_id: str            # Owner of this document
    course_id: str          # Which course this belongs to
    filename: str
    original_filename: str = ""  # Original uploaded filename
    content_text: str
    content_type: str = "text"   # "text", "pdf", "docx", "pptx"
    file_size: int = 0           # Size in bytes
    status: DocumentStatus = DocumentStatus.UPLOADED
    gridfs_id: str | None = None
    created_at: datetime = Field(default_factory=_utc_now)

    def to_dict(self):
        """Convert model to dictionary for MongoDB."""
        return self.model_dump(by_alias=True)


class Summary(BaseModel):
    """A summary generated for a course."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="_id")
    user_id: str
    course_id: str
    document_id: str  # Source document
    content: str  # The summary text
    language: Language = Language.HEBREW
    created_at: datetime = Field(default_factory=_utc_now)

    def to_dict(self):
        """Convert model to dictionary for MongoDB."""
        return self.model_dump(by_alias=True)


class Flashcard(BaseModel):
    question: str
    answer: str


class FlashcardSet(BaseModel):
    """A set of flashcards for a course."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="_id")
    user_id: str
    course_id: str
    document_id: str  # Source document
    cards: List[Flashcard]
    language: Language = Language.HEBREW
    created_at: datetime = Field(default_factory=_utc_now)

    def to_dict(self):
        """Convert model to dictionary for MongoDB."""
        return self.model_dump(by_alias=True)


class AssessmentQuestion(BaseModel):
    question: str
    options: Optional[List[str]] = None
    correct_answer: str


class Assessment(BaseModel):
    """A quiz/assessment for a course."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="_id")
    user_id: str
    course_id: str
    document_id: str  # Source document
    questions: List[AssessmentQuestion]
    language: Language = Language.HEBREW
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
    user_id: Optional[str] = None  # Track which user created the task
    course_id: Optional[str] = None  # Which course this task belongs to
    task_type: str = ""  # "summary", "flashcards", "assess", "homework"
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    def to_dict(self):
        """Convert model to dictionary for MongoDB."""
        return self.model_dump(by_alias=True)


class SystemConfig(BaseModel):
    """System configuration for admin-configurable values."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default="system_config", alias="_id")
    max_prompts_per_day: int = 50  # Default daily prompt limit
    max_file_size_mb: int = 10  # Max file upload size
    max_courses_per_user: int = 20  # Max courses a user can create
    default_flashcards_count: int = 10
    default_questions_count: int = 5
    enabled_modules: List[str] = Field(default_factory=lambda: ["summary", "flashcards", "assess", "homework"])
    maintenance_mode: bool = False
    updated_at: datetime = Field(default_factory=_utc_now)

    def to_dict(self):
        """Convert model to dictionary for MongoDB."""
        return self.model_dump(by_alias=True)


class CourseTerm(BaseModel):
    """A glossary term extracted from course materials."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="_id")
    term: str  # The term/concept
    definition: str  # Definition or explanation
    source_file: str = ""  # Source document filename
    course_id: str = ""  # Which course this term belongs to
    user_id: str  # Owner of this term
    created_at: datetime = Field(default_factory=_utc_now)

    def to_dict(self):
        """Convert model to dictionary for MongoDB."""
        return self.model_dump(by_alias=True)


class TutorSession(BaseModel):
    """Interactive tutor session with step-by-step learning."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="_id")
    user_id: str
    course_id: str = ""  # Optional course association
    topic: str  # What the user wants to learn
    syllabus: List[str] = Field(default_factory=list)  # List of steps/concepts
    current_step: int = 0  # Which step the user is on (0-indexed)
    chat_history: List[Dict] = Field(default_factory=list)  # Chat messages
    completed_steps: List[int] = Field(default_factory=list)  # Which steps are done
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    def to_dict(self):
        """Convert model to dictionary for MongoDB."""
        return self.model_dump(by_alias=True)
