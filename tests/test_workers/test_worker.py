import pytest
import json
from unittest.mock import MagicMock, patch
from src.domain.models.db_models import TaskStatus, Document

# Import worker module once at module level with proper patching
@pytest.fixture
def worker_module():
    """Fixture to import worker module with mocked dependencies."""
    with patch('worker.task_repo') as mock_task_repo, \
         patch('worker.doc_repo') as mock_doc_repo, \
         patch('worker.summary_service') as mock_summary, \
         patch('worker.flashcards_service') as mock_flashcards, \
         patch('worker.assess_service') as mock_assess, \
         patch('worker.homework_service') as mock_homework:
        
        import worker
        yield {
            'process_task': worker.process_task,
            'task_repo': mock_task_repo,
            'doc_repo': mock_doc_repo,
            'summary_service': mock_summary,
            'flashcards_service': mock_flashcards,
            'assess_service': mock_assess,
            'homework_service': mock_homework
        }


class TestWorkerTaskProcessing:
    """Tests for worker task processing logic."""

    @patch('worker.task_repo')
    @patch('worker.doc_repo')
    @patch('worker.summary_service')
    def test_process_summarize_task_success(self, mock_summary_service, mock_doc_repo, mock_task_repo):
        """Test successful processing of a summarize task."""
        from worker import process_task
        
        # Setup
        mock_doc = MagicMock()
        mock_doc.id = "doc-123"
        mock_doc.content_text = "Test document content"
        mock_doc_repo.get_by_id.return_value = mock_doc
        mock_summary_service.generate_summary.return_value = "summary_doc-123"
        
        task_data = {
            "task_id": "task-abc",
            "queue_name": "summarize",
            "document_id": "doc-123"
        }
        body = json.dumps(task_data).encode()
        
        # Execute
        process_task(body)
        
        # Verify
        mock_task_repo.update_status.assert_any_call("task-abc", TaskStatus.PROCESSING)
        mock_doc_repo.get_by_id.assert_called_with("doc-123")
        mock_summary_service.generate_summary.assert_called_once()
        mock_task_repo.update_status.assert_called_with("task-abc", TaskStatus.COMPLETED, result_id="summary_doc-123")

    @patch('worker.task_repo')
    @patch('worker.doc_repo')
    @patch('worker.flashcards_service')
    def test_process_flashcards_task_success(self, mock_flashcards_service, mock_doc_repo, mock_task_repo):
        """Test successful processing of a flashcards task."""
        from worker import process_task
        
        mock_doc = MagicMock()
        mock_doc.id = "doc-456"
        mock_doc.content_text = "Test content for flashcards"
        mock_doc_repo.get_by_id.return_value = mock_doc
        mock_flashcards_service.generate_flashcards.return_value = "flashcards_doc-456"
        
        task_data = {
            "task_id": "task-def",
            "queue_name": "flashcards",
            "document_id": "doc-456",
            "num_cards": 10
        }
        body = json.dumps(task_data).encode()
        
        process_task(body)
        
        mock_flashcards_service.generate_flashcards.assert_called_once()
        mock_task_repo.update_status.assert_called_with("task-def", TaskStatus.COMPLETED, result_id="flashcards_doc-456")

    @patch('worker.task_repo')
    @patch('worker.doc_repo')
    def test_process_task_document_not_found(self, mock_doc_repo, mock_task_repo):
        """Test handling when document is not found."""
        from worker import process_task
        from src.domain.errors import DocumentNotFoundError
        
        mock_doc_repo.get_by_id.return_value = None
        
        task_data = {
            "task_id": "task-xyz",
            "queue_name": "summarize",
            "document_id": "nonexistent-doc"
        }
        body = json.dumps(task_data).encode()
        
        # The worker raises DocumentNotFoundError, and tenacity will retry 3 times
        with pytest.raises((DocumentNotFoundError, Exception)):
            process_task(body)

    @patch('worker.task_repo')
    @patch('worker.homework_service')
    def test_process_homework_task_success(self, mock_homework_service, mock_task_repo):
        """Test successful processing of a homework task."""
        from worker import process_task
        
        mock_homework_service.solve_homework_problem.return_value = "Solution: x = 5"
        
        task_data = {
            "task_id": "task-hw",
            "queue_name": "homework",
            "problem_statement": "Solve for x: 2x + 5 = 15"
        }
        body = json.dumps(task_data).encode()
        
        process_task(body)
        
        mock_homework_service.solve_homework_problem.assert_called_with("Solve for x: 2x + 5 = 15")
        mock_task_repo.update_status.assert_called_with("task-hw", TaskStatus.COMPLETED, result_id="Solution: x = 5")

    @patch('worker.task_repo')
    def test_process_task_unknown_queue(self, mock_task_repo):
        """Test handling of unknown queue name."""
        from worker import process_task
        
        task_data = {
            "task_id": "task-unknown",
            "queue_name": "unknown_queue"
        }
        body = json.dumps(task_data).encode()
        
        # Unknown queue will cause ValueError, and tenacity will retry
        with pytest.raises((ValueError, Exception)):
            process_task(body)
