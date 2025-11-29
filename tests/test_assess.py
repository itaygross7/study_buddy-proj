import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_create_quiz():
    """
    Test the create quiz endpoint.
    """
    response = client.post("/api/v1/create-quiz", data={"text": "This is a test."})
    assert response.status_code == 200
    assert "quiz" in response.json()
