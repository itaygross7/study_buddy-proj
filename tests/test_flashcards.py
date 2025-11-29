import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_generate_flashcards():
    """
    Test the generate flashcards endpoint.
    """
    response = client.post("/api/v1/generate-flashcards", data={"text": "This is a test."})
    assert response.status_code == 200
    assert "flashcards" in response.json()
