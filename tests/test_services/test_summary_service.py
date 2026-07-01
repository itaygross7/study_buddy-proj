import unittest
from unittest.mock import MagicMock, patch

from src.services import summary_service
from src.domain.models.db_models import DocumentStatus


class TestSummaryService(unittest.TestCase):
    """Tests for summary_service.generate_summary."""

    @patch('src.services.summary_service.get_smart_context')
    @patch('src.services.summary_service.ai_client')
    def test_generate_summary_document_success(self, mock_ai_client, mock_smart_context):
        """Generate a summary for a single document using smart context."""
        mock_db_conn = MagicMock()
        mock_ai_client.generate_text.return_value = "This is a test summary."
        mock_smart_context.return_value = "Document context for the summary."

        mock_db_conn.documents.find_one.return_value = {
            "_id": "doc123",
            "content_text": "fallback text",
            "course_id": "course-1",
            "status": DocumentStatus.READY.value,
        }

        result_id = summary_service.generate_summary(
            document_id="doc123",
            query="general summary",
            db_conn=mock_db_conn,
        )

        self.assertEqual(result_id, "summary_doc_doc123")
        mock_ai_client.generate_text.assert_called_once()
        mock_db_conn.summaries.insert_one.assert_called_once()

        saved_data = mock_db_conn.summaries.insert_one.call_args[0][0]
        self.assertEqual(saved_data["_id"], result_id)
        self.assertEqual(saved_data["document_id"], "doc123")
        self.assertEqual(saved_data["summary_text"], "This is a test summary.")


if __name__ == '__main__':
    unittest.main()
