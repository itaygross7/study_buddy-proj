import pytest
from unittest.mock import patch, MagicMock

def test_trigger_flashcards_success(client):
    """
    Test the flashcards endpoint triggers a task successfully.
    """
    with patch('src.api.routes_flashcards.create_task') as mock_create_task, \
         patch('src.api.routes_flashcards.publish_task') as mock_publish:
        mock_create_task.return_value = "test-task-id-456"
        
        response = client.post('/api/flashcards/', 
                               json={"document_id": "doc-123", "num_cards": 5},
                               content_type='application/json')
        
        assert response.status_code == 202
        assert response.json['task_id'] == "test-task-id-456"
        assert response.json['status'] == "PENDING"
        mock_publish.assert_called_once()

def test_trigger_flashcards_invalid_num_cards(client):
    """
    Test the flashcards endpoint returns 400 for invalid num_cards.
    """
    response = client.post('/api/flashcards/', 
                           json={"document_id": "doc-123", "num_cards": 0},
                           content_type='application/json')
    
    assert response.status_code == 400
    assert 'error' in response.json
