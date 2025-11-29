import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_solve_problem():
    """
    Test the solve problem endpoint.
    """
    response = client.post("/api/v1/solve-problem", data={"problem": "This is a test."})
    assert response.status_code == 200
    assert "solution" in response.json()
