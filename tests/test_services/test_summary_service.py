import unittest
from unittest.mock import MagicMock, patch
from src.services import summary_service


class TestSummaryService(unittest.TestCase):

    @patch('src.services.summary_service.ai_client')
    def test_generate_summary_success(self, mock_ai_client):
        # Arrange
        mock_db_conn = MagicMock()
        mock_ai_client.generate_text.return_value = "This is a test summary."

        doc_id = "doc123"
        doc_content = "This is the original document content."

        # Act
        result_id = summary_service.generate_summary(doc_id, doc_content, db_conn=mock_db_conn)

        # Assert
        self.assertTrue(result_id.startswith("summary_"))
        # Verify the AI client was called correctly
        mock_ai_client.generate_text.assert_called_once()
        # Verify the database was called to save the result
        mock_db_conn.summaries.insert_one.assert_called_once()

        # Check the content of the saved data
        saved_data = mock_db_conn.summaries.insert_one.call_args[0][0]
        self.assertEqual(saved_data['_id'], result_id)
        self.assertEqual(saved_data['document_id'], doc_id)
        self.assertEqual(saved_data['summary_text'], "This is a test summary.")


if __name__ == '__main__':
    unittest.main()
