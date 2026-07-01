import pytest
import os
from unittest.mock import MagicMock, patch


# Set required environment variables before any imports
@pytest.fixture(scope='session', autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ.setdefault('SECRET_KEY', 'test-secret-key')
    os.environ.setdefault('MONGO_URI', 'mongodb://localhost:27017/test')
    os.environ.setdefault('RABBITMQ_URI', 'amqp://guest:guest@localhost:5672')
    os.environ.setdefault('FLASK_ENV', 'testing')
    yield


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


@pytest.fixture
def authenticated_client(client):
    """Test client with a logged-in user session."""
    from src.domain.models.db_models import User, UserRole

    user = User(
        _id="test-user-id",
        email="test@example.com",
        password_hash="hash",
        role=UserRole.USER,
        is_active=True,
    )
    with patch('src.api.routes_auth.auth_service.get_user_by_id', return_value=user):
        with client.session_transaction() as sess:
            sess['_user_id'] = 'test-user-id'
            sess['_fresh'] = True
        yield client
