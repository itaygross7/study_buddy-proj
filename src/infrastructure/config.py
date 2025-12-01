import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import secrets

load_dotenv()

def _generate_default_secret_key():
    """Generate a secure default secret key for development only."""
    return secrets.token_hex(32)

class Settings(BaseSettings):
    """
    Pydantic-based settings management.
    Reads environment variables and provides them to the application.
    """
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file='.env',
        env_file_encoding='utf-8'
    )
    
    # Flask
    FLASK_ENV: str = Field(default='development')
    SECRET_KEY: str = Field(default_factory=_generate_default_secret_key)

    # Infrastructure
    MONGO_URI: str = Field(default='mongodb://localhost:27017/studybuddy')
    RABBITMQ_URI: str = Field(default='amqp://guest:guest@localhost:5672/')

    # AI Services - API Keys
    OPENAI_API_KEY: str = Field(default='')
    GEMINI_API_KEY: str = Field(default='')
    
    # AI Services - Model Configuration (SB_* prefix for StudyBuddy)
    SB_OPENAI_MODEL: str = Field(default='gpt-4o-mini')
    SB_GEMINI_MODEL: str = Field(default='gemini-1.5-flash')
    SB_DEFAULT_PROVIDER: str = Field(default='gemini')
    SB_BASE_URL: str = Field(default='')  # Optional custom base URL for API

    # Logging
    LOG_LEVEL: str = Field(default='INFO')
    
    # Admin Configuration
    ADMIN_EMAIL: str = Field(default='')  # Admin email address
    
    # Email Configuration (SMTP)
    MAIL_SERVER: str = Field(default='smtp.gmail.com')
    MAIL_PORT: int = Field(default=587)
    MAIL_USE_TLS: bool = Field(default=True)
    MAIL_USERNAME: str = Field(default='')
    MAIL_PASSWORD: str = Field(default='')
    MAIL_DEFAULT_SENDER: str = Field(default='')
    
    # Security
    SESSION_COOKIE_SECURE: bool = Field(default=False)  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY: bool = Field(default=True)
    SESSION_COOKIE_SAMESITE: str = Field(default='Lax')

settings = Settings()
