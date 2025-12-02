from unittest.mock import MagicMock
from datetime import datetime, timezone
from src.infrastructure.repositories import MongoDocumentRepository, MongoTaskRepository
from src.domain.models.db_models import Document, TaskStatus


class TestMongoDocumentRepository:
    """Tests for MongoDocumentRepository."""

    def test_get_by_id_found(self):
        """Test retrieving an existing document."""
        mock_db = MagicMock()
        mock_db.documents.find_one.return_value = {
            "_id": "doc-123",
            "user_id": "user-123",
            "course_id": "course-123",
            "filename": "test.pdf",
            "content_text": "Test content",
            "created_at": datetime.now(timezone.utc)
        }

        repo = MongoDocumentRepository(mock_db)
        doc = repo.get_by_id("doc-123")

        assert doc is not None
        assert doc.id == "doc-123"
        assert doc.filename == "test.pdf"
        assert doc.content_text == "Test content"
        mock_db.documents.find_one.assert_called_with({"_id": "doc-123"})

    def test_get_by_id_not_found(self):
        """Test retrieving a non-existent document."""
        mock_db = MagicMock()
        mock_db.documents.find_one.return_value = None

        repo = MongoDocumentRepository(mock_db)
        doc = repo.get_by_id("nonexistent-id")

        assert doc is None

    def test_create_document(self):
        """Test creating a new document."""
        mock_db = MagicMock()

        repo = MongoDocumentRepository(mock_db)
        document = Document(
            _id="new-doc-123",
            user_id="user-123",
            course_id="course-123",
            filename="new_file.txt",
            content_text="New file content"
        )
        repo.create(document)

        mock_db.documents.insert_one.assert_called_once()
        call_args = mock_db.documents.insert_one.call_args[0][0]
        assert call_args["_id"] == "new-doc-123"
        assert call_args["filename"] == "new_file.txt"


class TestMongoTaskRepository:
    """Tests for MongoTaskRepository."""

    def test_get_by_id_found(self):
        """Test retrieving an existing task."""
        mock_db = MagicMock()
        now = datetime.now(timezone.utc)
        mock_db.tasks.find_one.return_value = {
            "_id": "task-abc",
            "status": "PENDING",
            "result_id": None,
            "error_message": None,
            "created_at": now,
            "updated_at": now
        }

        repo = MongoTaskRepository(mock_db)
        task = repo.get_by_id("task-abc")

        assert task is not None
        assert task.id == "task-abc"
        assert task.status == TaskStatus.PENDING

    def test_get_by_id_not_found(self):
        """Test retrieving a non-existent task."""
        mock_db = MagicMock()
        mock_db.tasks.find_one.return_value = None

        repo = MongoTaskRepository(mock_db)
        task = repo.get_by_id("nonexistent-id")

        assert task is None

    def test_create_task(self):
        """Test creating a new task."""
        mock_db = MagicMock()

        repo = MongoTaskRepository(mock_db)
        task = repo.create()

        assert task is not None
        assert task.status == TaskStatus.PENDING
        mock_db.tasks.insert_one.assert_called_once()

    def test_update_status_to_processing(self):
        """Test updating task status to PROCESSING."""
        mock_db = MagicMock()

        repo = MongoTaskRepository(mock_db)
        repo.update_status("task-xyz", TaskStatus.PROCESSING)

        mock_db.tasks.update_one.assert_called_once()
        call_args = mock_db.tasks.update_one.call_args
        assert call_args[0][0] == {"_id": "task-xyz"}
        assert call_args[0][1]["$set"]["status"] == "PROCESSING"

    def test_update_status_to_completed_with_result(self):
        """Test updating task status to COMPLETED with result."""
        mock_db = MagicMock()

        repo = MongoTaskRepository(mock_db)
        repo.update_status("task-xyz", TaskStatus.COMPLETED, result_id="result-123")

        call_args = mock_db.tasks.update_one.call_args[0][1]
        assert call_args["$set"]["status"] == "COMPLETED"
        assert call_args["$set"]["result_id"] == "result-123"

    def test_update_status_to_failed_with_error(self):
        """Test updating task status to FAILED with error message."""
        mock_db = MagicMock()

        repo = MongoTaskRepository(mock_db)
        repo.update_status("task-xyz", TaskStatus.FAILED, error_message="Something went wrong")

        call_args = mock_db.tasks.update_one.call_args[0][1]
        assert call_args["$set"]["status"] == "FAILED"
        assert call_args["$set"]["error_message"] == "Something went wrong"
