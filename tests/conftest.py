import pytest
from app import create_app

@pytest.fixture(scope='module')
def app():
    """Create and configure a new app instance for each test module."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        # Use in-memory DB or mongomock for tests
        "MONGO_URI": "mongomock://localhost/testdb",
    })
    yield app

@pytest.fixture(scope='module')
def client(app):
    """A test client for the app."""
    return app.test_client()
