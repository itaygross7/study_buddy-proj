import pytest
from unittest.mock import MagicMock, patch
from src.services.task_service import create_task, get_task, update_task_status
from src.domain.models.db_models import TaskStatus


class TestTaskService:
    """Tests for the task service."""

    @patch('src.services.task_service._get_db')
    def test_create_task_success(self, mock_get_db):
        """Test successful task creation."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        task_id = create_task()
        
        assert task_id is not None
        assert isinstance(task_id, str)
        assert len(task_id) == 36  # UUID format
        mock_db.tasks.insert_one.assert_called_once()

    @patch('src.services.task_service._get_db')
    def test_get_task_found(self, mock_get_db):
        """Test retrieving an existing task."""
        from datetime import datetime, timezone
        
        mock_db = MagicMock()
        now = datetime.now(timezone.utc)
        mock_db.tasks.find_one.return_value = {
            "_id": "test-task-id",
            "status": "PROCESSING",
            "result_id": None,
            "error_message": None,
            "created_at": now,
            "updated_at": now
        }
        mock_get_db.return_value = mock_db
        
        task = get_task("test-task-id")
        
        assert task is not None
        assert task.id == "test-task-id"
        assert task.status == TaskStatus.PROCESSING

    @patch('src.services.task_service._get_db')
    def test_get_task_not_found(self, mock_get_db):
        """Test retrieving a non-existent task."""
        mock_db = MagicMock()
        mock_db.tasks.find_one.return_value = None
        mock_get_db.return_value = mock_db
        
        task = get_task("nonexistent-id")
        
        assert task is None

    @patch('src.services.task_service._get_db')
    def test_update_task_status_to_completed(self, mock_get_db):
        """Test updating task status to completed."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        update_task_status(
            "test-task-id",
            TaskStatus.COMPLETED,
            result_id="result-123"
        )
        
        mock_db.tasks.update_one.assert_called_once()
        call_args = mock_db.tasks.update_one.call_args[0][1]
        assert call_args["$set"]["status"] == "COMPLETED"
        assert call_args["$set"]["result_id"] == "result-123"

    @patch('src.services.task_service._get_db')
    def test_update_task_status_to_failed(self, mock_get_db):
        """Test updating task status to failed with error message."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        update_task_status(
            "test-task-id",
            TaskStatus.FAILED,
            error_message="Processing failed"
        )
        
        call_args = mock_db.tasks.update_one.call_args[0][1]
        assert call_args["$set"]["status"] == "FAILED"
        assert call_args["$set"]["error_message"] == "Processing failed"

    @patch('src.services.task_service._get_db')
    def test_update_task_status_with_custom_db(self, mock_get_db):
        """Test updating task status with a custom database connection."""
        custom_db = MagicMock()
        main_db = MagicMock()
        mock_get_db.return_value = custom_db
        
        update_task_status("test-id", TaskStatus.PROCESSING, db_conn=custom_db)
        
        custom_db.tasks.update_one.assert_called_once()
