"""
Configuration settings for ElevenLabs Voice Cloning Service
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # ElevenLabs API Configuration
    elevenlabs_api_key: str
    elevenlabs_base_url: str = "https://api.elevenlabs.io/v1"

    # Service Configuration
    app_name: str = "MyMemori.es Voice Cloning Service"
    app_version: str = "1.0.0"
    debug: bool = False

    # File Management
    output_directory: str = "./output"
    max_file_size_mb: int = 50
    allowed_extensions: list = [".wav", ".mp3"]

    # Voice Management
    max_voice_retries: int = 3
    voice_cleanup_enabled: bool = True

    # Queue Configuration
    redis_url: str = "redis://localhost:6379/0"
    queue_name: str = "voice_cloning_queue"
    max_concurrent_jobs: int = 5

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hour

    # Notification Configuration
    mock_webhook_enabled: bool = True
    notification_email_from: str = "noreply@mymemori.es"

    # Resend Email Configuration
    resend_api_key: str
    from_email: str = "noreply@mymemori.es"
    from_name: str = "MyMemori.es"

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get application settings"""
    return settings