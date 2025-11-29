import os
from dotenv import load_dotenv
from pydantic import BaseSettings, Field

load_dotenv()

class Settings(BaseSettings):
    """
    Pydantic-based settings management.
    Reads environment variables and provides them to the application.
    """
    # Flask
    FLASK_ENV: str = Field(..., env='FLASK_ENV')
    SECRET_KEY: str = Field(..., env='SECRET_KEY')

    # Infrastructure
    MONGO_URI: str = Field(..., env='MONGO_URI')
    RABBITMQ_URI: str = Field(..., env='RABBITMQ_URI')

    # AI Services
    OPENAI_API_KEY: str = Field(..., env='OPENAI_API_KEY')
    GEMINI_API_KEY: str = Field(..., env='GEMINI_API_KEY')

    # Logging
    LOG_LEVEL: str = Field('INFO', env='LOG_LEVEL')

    class Config:
        case_sensitive = True
        env_file = '.env'
        env_file_encoding = 'utf-8'

settings = Settings()
