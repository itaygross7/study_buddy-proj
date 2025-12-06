import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # --- Core App Settings ---
    FLASK_ENV: str = "production"
    SECRET_KEY: str
    DEBUG: bool = False

    # --- Infrastructure ---
    MONGO_URI: str
    RABBITMQ_URI: str

    # --- AI Services ---
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    
    # AI Model Configuration
    SB_OPENAI_MODEL: str = "gpt-4o-mini"
    SB_GEMINI_MODEL: str = "gemini-1.5-flash"
    SB_DEFAULT_PROVIDER: str = "gemini"
    SB_BASE_URL: str = ""

    # --- Security ---
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = 'Lax'

    # --- OAuth ---
    BASE_URL: str = ""  # Base URL for OAuth redirects (e.g., https://yourdomain.com)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    APPLE_CLIENT_ID: str = ""
    APPLE_TEAM_ID: str = ""
    APPLE_KEY_ID: str = ""
    APPLE_PRIVATE_KEY: str = ""

    # --- Email Service ---
    MAIL_SERVER: str = ""
    MAIL_PORT: int = 587
    MAIL_USE_TLS: bool = True
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_DEFAULT_SENDER: str = "noreply@studybuddy.ai"
    ADMIN_EMAIL: str = ""

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    # --- Webhook ---
    WEBHOOK_SECRET: str = ""
    
    # --- Version for cache busting ---
    VERSION: str = "2024.12.06"

# Load settings
settings = Settings()

# Production readiness checks
if settings.FLASK_ENV == "production":
    if not settings.SECRET_KEY or settings.SECRET_KEY == "change-this-to-a-very-secret-key-in-production":
        raise ValueError("CRITICAL: SECRET_KEY is not set for production.")
    if settings.DEBUG:
        raise ValueError("CRITICAL: DEBUG mode must be disabled in production.")
    if not settings.ADMIN_EMAIL:
        print("WARNING: ADMIN_EMAIL is not set. Error notifications will not be sent.")
