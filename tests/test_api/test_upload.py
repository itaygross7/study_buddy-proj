import io
from flask.testing import FlaskClient

def test_upload_file_success(client: FlaskClient):
    """
    Test successful file upload and processing.
    """
    data = {
        'file': (io.BytesIO(b"this is a test file"), 'test.txt')
    }
    response = client.post('/api/upload/', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 201
    assert 'document_id' in response.json
    assert response.json['filename'] == 'test.txt'

def test_upload_no_file(client: FlaskClient):
    """
    Test upload request with no file part.
    """
    response = client.post('/api/upload/', data={}, content_type='multipart/form-data')
    assert response.status_code == 400
    assert 'error' in response.json
    assert 'No file part' in response.json['error']
