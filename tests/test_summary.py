import pytest
from unittest.mock import patch, MagicMock

def test_trigger_summary_success(client):
    """
    Test the summary endpoint triggers a task successfully.
    """
    with patch('src.api.routes_summary.create_task') as mock_create_task, \
         patch('src.api.routes_summary.publish_task') as mock_publish:
        mock_create_task.return_value = "test-task-id-123"
        
        response = client.post('/api/summary/', 
                               json={"document_id": "doc-123"},
                               content_type='application/json')
        
        assert response.status_code == 202
        assert response.json['task_id'] == "test-task-id-123"
        assert response.json['status'] == "PENDING"
        mock_publish.assert_called_once()

def test_trigger_summary_missing_document_id(client):
    """
    Test the summary endpoint returns 400 for missing document_id.
    """
    response = client.post('/api/summary/', 
                           json={},
                           content_type='application/json')
    
    assert response.status_code == 400
    assert 'error' in response.json
