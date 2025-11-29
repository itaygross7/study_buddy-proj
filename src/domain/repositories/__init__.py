from abc import ABC, abstractmethod
from typing import Optional
from ..models.db_models import Document, Task, TaskStatus

class IDocumentRepository(ABC):
    """Interface for a document repository."""
    @abstractmethod
    def get_by_id(self, doc_id: str) -> Optional[Document]:
        pass

    @abstractmethod
    def create(self, document: Document) -> None:
        pass

class ITaskRepository(ABC):
    """Interface for a task repository."""
    @abstractmethod
    def get_by_id(self, task_id: str) -> Optional[Task]:
        pass

    @abstractmethod
    def create(self) -> Task:
        pass

    @abstractmethod
    def update_status(self, task_id: str, status: TaskStatus, result_id: Optional[str] = None, error_message: Optional[str] = None) -> None:
        pass
