import pytest
from unittest.mock import patch, MagicMock

def test_trigger_homework_success(client):
    """
    Test the homework endpoint triggers a task successfully.
    """
    with patch('src.api.routes_homework.create_task') as mock_create_task, \
         patch('src.api.routes_homework.publish_task') as mock_publish:
        mock_create_task.return_value = "test-task-id-abc"
        
        response = client.post('/api/homework/', 
                               json={"problem_statement": "Solve for x: 2x + 5 = 15"},
                               content_type='application/json')
        
        assert response.status_code == 202
        assert response.json['task_id'] == "test-task-id-abc"
        assert response.json['status'] == "PENDING"
        mock_publish.assert_called_once()

def test_trigger_homework_missing_problem(client):
    """
    Test the homework endpoint returns 400 for missing problem_statement.
    """
    response = client.post('/api/homework/', 
                           json={},
                           content_type='application/json')
    
    assert response.status_code == 400
    assert 'error' in response.json

def test_trigger_homework_hebrew_input(client):
    """
    Test the homework endpoint handles Hebrew input correctly.
    """
    with patch('src.api.routes_homework.create_task') as mock_create_task, \
         patch('src.api.routes_homework.publish_task') as mock_publish:
        mock_create_task.return_value = "test-task-hebrew"
        
        response = client.post('/api/homework/', 
                               json={"problem_statement": "פתור את המשוואה: 2x + 5 = 15"},
                               content_type='application/json')
        
        assert response.status_code == 202
        assert response.json['task_id'] == "test-task-hebrew"
        mock_publish.assert_called_once()
