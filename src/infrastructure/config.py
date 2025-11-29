import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

load_dotenv()

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
    SECRET_KEY: str = Field(default='dev-secret-key-change-in-production')

    # Infrastructure
    MONGO_URI: str = Field(default='mongodb://localhost:27017/studybuddy')
    RABBITMQ_URI: str = Field(default='amqp://guest:guest@localhost:5672/')

    # AI Services
    OPENAI_API_KEY: str = Field(default='')
    GEMINI_API_KEY: str = Field(default='')

    # Logging
    LOG_LEVEL: str = Field(default='INFO')

settings = Settings()
