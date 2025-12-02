"""
Legacy test file for tools API.
These tests are deprecated as the API structure has changed.
The tests use the new app factory pattern via conftest.py fixtures.
"""
import io
from unittest.mock import patch, MagicMock


def test_upload_file_success_returns_document_id(client):
    """
    Test upload endpoint processes a valid text file.
    """
    with patch('src.api.routes_upload.MongoDocumentRepository') as mock_repo_class:
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        data = {
            "file": (io.BytesIO(b"test file content"), "test.txt")
        }
        response = client.post(
            "/api/upload/",
            data=data,
            content_type="multipart/form-data"
        )
        # Should return 201 with document_id
        assert response.status_code == 201
        assert 'document_id' in response.json
        mock_repo.create.assert_called_once()


def test_summary_api_requires_document_id(client):
    """
    Test that summary endpoint requires document_id.
    """
    response = client.post(
        '/api/summary/',
        json={},
        content_type='application/json'
    )
    assert response.status_code == 400
    assert 'error' in response.json
