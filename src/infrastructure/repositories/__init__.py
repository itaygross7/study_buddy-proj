import uuid
from datetime import datetime, timezone
from typing import Optional, Union

from pymongo.database import Database

from src.domain.repositories import IDocumentRepository, ITaskRepository
from src.domain.models.db_models import Document, Task, TaskStatus
from sb_utils.logger_utils import logger


class MongoDocumentRepository(IDocumentRepository):
    """MongoDB implementation of the document repository."""

    def __init__(self, db: Database):
        self.db = db

    def get_by_id(self, doc_id: str) -> Optional[Document]:
        doc_data = self.db.documents.find_one({"_id": doc_id})
        return Document(**doc_data) if doc_data else None

    def create(self, document: Document) -> None:
        self.db.documents.insert_one(document.to_dict())
        logger.info(f"Created document '{document.filename}' with ID: {document.id}")


class MongoTaskRepository(ITaskRepository):
    """MongoDB implementation of the task repository."""

    def __init__(self, db: Database):
        self.db = db

    def get_by_id(self, task_id: str) -> Optional[Task]:
        task_data = self.db.tasks.find_one({"_id": task_id})
        return Task(**task_data) if task_data else None

    def create(
        self,
        data: Union[Task, dict, None] = None,
        user_id: Optional[str] = None,
        document_id: Optional[str] = None,
        task_type: str = "",
    ) -> Task:
        """
        Universal create method:

        Supports three styles:

        1. New style:
           - create(task: Task)

        2. Dict style:
           - create({"_id": ..., "user_id": ..., ...})

        3. Old style (backwards compatible):
           - create(user_id=user_id, document_id=document_id, task_type="file_processing")
        """
        now = datetime.now(timezone.utc)

        # CASE 1: Full Task object provided
        if isinstance(data, Task):
            task = data

        # CASE 2: Raw dict provided
        elif isinstance(data, dict):
            task = Task(**data)

        # CASE 3: Old-style call using explicit parameters
        else:
            task = Task(
                _id=str(uuid.uuid4()),
                status=TaskStatus.PENDING,
                user_id=user_id,
                # NOTE: in the legacy API, document_id was stored as result_id
                result_id=document_id,
                task_type=task_type,
                created_at=now,
                updated_at=now,
            )

        self.db.tasks.insert_one(task.to_dict())
        logger.info(f"Created new task with ID: {task.id}")
        return task

    def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        result_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        update_doc = {
            "$set": {
                "status": status.value,
                "updated_at": datetime.now(timezone.utc),
            }
        }
        if result_id is not None:
            update_doc["$set"]["result_id"] = result_id
        if error_message is not None:
            update_doc["$set"]["error_message"] = error_message

        self.db.tasks.update_one({"_id": task_id}, update_doc)
        logger.info(f"Updated task {task_id} to status: {status.value}")
