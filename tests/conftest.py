import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture(scope='module')
def app():
    """Create and configure a new app instance for each test module."""
    # Mock the database before importing the app
    with patch('src.infrastructure.database.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        from app import create_app
        app = create_app()
        app.config.update({
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
        })
        yield app

@pytest.fixture(scope='module')
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def mock_db():
    """Provides a mocked MongoDB database."""
    return MagicMock()
