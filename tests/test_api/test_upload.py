import io
from unittest.mock import patch, MagicMock
from flask.testing import FlaskClient


def test_upload_file_success(client: FlaskClient):
    """
    Test successful file upload and processing.
    """
    with patch('src.api.routes_upload.MongoDocumentRepository') as mock_repo_class:
        mock_repo_instance = MagicMock()
        mock_repo_class.return_value = mock_repo_instance

        data = {
            'file': (io.BytesIO(b"this is a test file"), 'test.txt')
        }
        response = client.post('/api/upload/', data=data, content_type='multipart/form-data')

        assert response.status_code == 201
        assert 'document_id' in response.json
        assert response.json['filename'] == 'test.txt'
        mock_repo_instance.create.assert_called_once()


def test_upload_no_file(client: FlaskClient):
    """
    Test upload request with no file part.
    """
    response = client.post('/api/upload/', data={}, content_type='multipart/form-data')
    assert response.status_code == 400
    assert 'error' in response.json
    assert 'No file part' in response.json['error']
