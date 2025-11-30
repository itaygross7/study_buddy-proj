import io
import pytest
from unittest.mock import patch, MagicMock
from src.api import app

@pytest.fixture
def client():
    app.testing = True
    with app.test_client() as c:
        yield c

def test_summarize_empty(client):
    r = client.post("/api/summarize", data={})
    assert r.status_code == 400
    assert "לא הוזן טקסט" in r.get_json().get("error", "")

@patch("src.api.ai_service")
def test_summarize_text(mock_ai_service, client):
    mock_ai_service.call = MagicMock(return_value="תקציר לבדיקה")
    r = client.post("/api/summarize", data={"text": "זה טקסט לבדיקה"})
    assert r.status_code == 200
    assert r.get_json()["summary"] == "תקציר לבדיקה"

def test_upload_wrong_type(client):
    data = {
        "file": (io.BytesIO(b"dummy"), "test.exe")
    }
    r = client.post("/api/summarize", data=data, content_type="multipart/form-data")
    # Should return 400 with friendly message
    assert r.status_code in (400, 413)

# Additional tests (AI error / DB failure) should mock services similarly.

