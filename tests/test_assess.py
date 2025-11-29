import pytest
from unittest.mock import patch, MagicMock

def test_trigger_assessment_success(client):
    """
    Test the assess endpoint triggers a task successfully.
    """
    with patch('src.api.routes_assess.create_task') as mock_create_task, \
         patch('src.api.routes_assess.publish_task') as mock_publish:
        mock_create_task.return_value = "test-task-id-789"
        
        response = client.post('/api/assess/', 
                               json={"document_id": "doc-123", "num_questions": 5, "question_type": "mcq"},
                               content_type='application/json')
        
        assert response.status_code == 202
        assert response.json['task_id'] == "test-task-id-789"
        assert response.json['status'] == "PENDING"
        mock_publish.assert_called_once()

def test_trigger_assessment_missing_document_id(client):
    """
    Test the assess endpoint returns 400 for missing document_id.
    """
    response = client.post('/api/assess/', 
                           json={"num_questions": 5},
                           content_type='application/json')
    
    assert response.status_code == 400
    assert 'error' in response.json
