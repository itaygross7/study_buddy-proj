import uuid
from datetime import datetime, timezone
from typing import Optional, Union

from bson import ObjectId
from pymongo.database import Database

from src.domain.repositories import IDocumentRepository, ITaskRepository
from src.domain.models.db_models import Document, Task, TaskStatus
from sb_utils.logger_utils import logger


class MongoDocumentRepository(IDocumentRepository):
    """MongoDB implementation of the document repository."""

    def __init__(self, db: Database):
        self.db = db
        self.collection = self.db.documents

    def _normalize_id(self, doc_id: str):
        """
        Try several strategies so we can survive different legacy schemas:
        - _id as plain string UUID
        - _id as ObjectId (string)
        - field 'id' instead of '_id'
        """
        # 1) Exact string _id
        doc = self.collection.find_one({"_id": doc_id})
        if doc:
            return doc

        # 2) Try as ObjectId
        try:
            oid = ObjectId(doc_id)
            doc = self.collection.find_one({"_id": oid})
            if doc:
                return doc
        except Exception:
            pass

        # 3) Legacy: 'id' field
        doc = self.collection.find_one({"id": doc_id})
        if doc:
            return doc

        return None

    def get_by_id(self, doc_id: str) -> Optional[Document]:
        doc_data = self._normalize_id(doc_id)
        if not doc_data:
            logger.warning(
                "MongoDocumentRepository.get_by_id.missing",
                extra={"doc_id": doc_id},
            )
            return None

        try:
            return Document(**doc_data)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "MongoDocumentRepository.get_by_id.parse_error",
                extra={"doc_id": doc_id, "error": str(exc)},
                exc_info=True,
            )
            return None

    def create(self, document: Document) -> None:
        doc_dict = document.to_dict()

        # Ensure we always have a proper _id in Mongo
        if "_id" not in doc_dict:
            # Common pattern: Document has .id attribute
            doc_dict["_id"] = getattr(document, "id", str(uuid.uuid4()))

        # Avoid duplicating both id and _id with different values
        if "id" in doc_dict and doc_dict["id"] != doc_dict["_id"]:
            logger.warning(
                "MongoDocumentRepository.create.id_mismatch",
                extra={"_id": doc_dict["_id"], "id": doc_dict["id"]},
            )

        self.collection.insert_one(doc_dict)
        logger.info(
            f"Created document '{getattr(document, 'filename', '?')}' with ID: {getattr(document, 'id', doc_dict.get('_id'))}"
        )

    def update(self, document: Document) -> None:
        """
        Update an existing document in Mongo.

        Uses document.id if available, otherwise _id from to_dict().
        """
        doc_dict = document.to_dict()
        # Extract the identifier
        doc_id = doc_dict.pop("_id", None) or getattr(document, "id", None)
        if not doc_id:
            raise ValueError("Document has no identifiable id/_id for update().")

        # Try to handle both string and ObjectId IDs
        query = {"_id": doc_id}
        try:
            # If stored as ObjectId, this will succeed
            query_objid = {"_id": ObjectId(str(doc_id))}
            result = self.collection.update_one(query_objid, {"$set": doc_dict})
            if result.matched_count == 0:
                # Fall back to plain string
                result = self.collection.update_one(query, {"$set": doc_dict})
        except Exception:
            result = self.collection.update_one(query, {"$set": doc_dict})

        if result.matched_count == 0:
            logger.warning(
                "MongoDocumentRepository.update.not_found",
                extra={"doc_id": str(doc_id)},
            )
        else:
            logger.info(
                "MongoDocumentRepository.update.ok",
                extra={"doc_id": str(doc_id)},
            )


class MongoTaskRepository(ITaskRepository):
    """MongoDB implementation of the task repository."""

    def __init__(self, db: Database):
        self.db = db
        self.collection = self.db.tasks

    def get_by_id(self, task_id: str) -> Optional[Task]:
        # Same normalization approach as documents
        task_data = (
            self.collection.find_one({"_id": task_id})
            or self.collection.find_one({"id": task_id})
        )
        if not task_data:
            logger.warning(
                "MongoTaskRepository.get_by_id.missing",
                extra={"task_id": task_id},
            )
            return None

        try:
            return Task(**task_data)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "MongoTaskRepository.get_by_id.parse_error",
                extra={"task_id": task_id, "error": str(exc)},
                exc_info=True,
            )
            return None

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
                # legacy semantics: document_id stored as result_id for file_processing
                result_id=document_id,
                task_type=task_type,
                created_at=now,
                updated_at=now,
            )

        task_dict = task.to_dict()

        # Ensure _id exists
        if "_id" not in task_dict:
            task_dict["_id"] = getattr(task, "id", str(uuid.uuid4()))

        self.collection.insert_one(task_dict)
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

        # Try both _id and id
        result = self.collection.update_one({"_id": task_id}, update_doc)
        if result.matched_count == 0:
            result = self.collection.update_one({"id": task_id}, update_doc)

        if result.matched_count == 0:
            logger.warning(
                "MongoTaskRepository.update_status.not_found",
                extra={"task_id": task_id, "status": status.value},
            )
        else:
            logger.info(
                f"Updated task {task_id} to status: {status.value}"
            )
