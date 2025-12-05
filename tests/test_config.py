"""
Test configuration settings to ensure all required fields are present.
"""
import pytest
import os


def test_sb_config_fields_exist():
    """Test that all SB_* configuration fields are present in Settings."""
    # Set required environment variables
    os.environ.setdefault('SECRET_KEY', 'test-secret-key')
    os.environ.setdefault('MONGO_URI', 'mongodb://localhost:27017/test')
    os.environ.setdefault('RABBITMQ_URI', 'amqp://localhost:5672/')
    os.environ.setdefault('FLASK_ENV', 'development')
    
    from src.infrastructure.config import settings
    
    # Verify all SB_* fields exist and have correct defaults
    assert hasattr(settings, 'SB_DEFAULT_PROVIDER'), "SB_DEFAULT_PROVIDER should exist"
    assert hasattr(settings, 'SB_BASE_URL'), "SB_BASE_URL should exist"
    assert hasattr(settings, 'SB_GEMINI_MODEL'), "SB_GEMINI_MODEL should exist"
    assert hasattr(settings, 'SB_OPENAI_MODEL'), "SB_OPENAI_MODEL should exist"
    
    # Verify default values
    assert settings.SB_DEFAULT_PROVIDER == "gemini", "Default provider should be gemini"
    assert settings.SB_BASE_URL == "", "Default base URL should be empty string"
    assert settings.SB_GEMINI_MODEL == "gemini-1.5-flash", "Default Gemini model should be gemini-1.5-flash"
    assert settings.SB_OPENAI_MODEL == "gpt-4o-mini", "Default OpenAI model should be gpt-4o-mini"


def test_ai_client_initialization():
    """Test that AIClient can be initialized with the settings."""
    # Set required environment variables
    os.environ.setdefault('SECRET_KEY', 'test-secret-key')
    os.environ.setdefault('MONGO_URI', 'mongodb://localhost:27017/test')
    os.environ.setdefault('RABBITMQ_URI', 'amqp://localhost:5672/')
    os.environ.setdefault('FLASK_ENV', 'development')
    os.environ.setdefault('GEMINI_API_KEY', 'test-key')
    
    from src.infrastructure.config import settings
    from src.services.ai_client import AIClient
    
    # This should not raise AttributeError anymore
    client = AIClient(provider=settings.SB_DEFAULT_PROVIDER)
    assert client.provider == "gemini", "Client provider should be gemini"
