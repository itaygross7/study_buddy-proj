import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_summarize_text():
    """
    Test the summarize text endpoint.
    """
    response = client.post("/api/v1/summarize", data={"text": "This is a test."})
    assert response.status_code == 200
    assert "summary" in response.json()
