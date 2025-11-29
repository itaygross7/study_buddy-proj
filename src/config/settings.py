from pydantic import BaseSettings
import os

class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables.
    """
    APP_NAME: str = "StudyBuddy"
    MONGO_URI: str = "mongodb://localhost:27017/"
    MONGO_DB_NAME: str = "studybuddy"
    REDIS_URI: str = "redis://localhost:6379/0"
    LOG_LEVEL: str = "INFO"
    OPENAI_API_KEY: str = "your_openai_key_here"
    GEMINI_API_KEY: str = "your_gemini_key_here"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
