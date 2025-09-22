"""
Pydantic models for API requests
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime


class VoiceCloneRequest(BaseModel):
    """Request model for voice cloning job"""

    voice_name: str = Field(..., min_length=1, max_length=100, description="Name for the voice clone")
    text: str = Field(..., min_length=1, max_length=5000, description="Text to synthesize with cloned voice")
    description: Optional[str] = Field(None, max_length=500, description="Optional voice description")
    model: str = Field("eleven_multilingual_v2", description="ElevenLabs model to use (eleven_multilingual_v2, eleven_v3, eleven_flash_v2_5, eleven_turbo_v2_5, etc.)")

    # Notification settings
    notification_email: Optional[str] = Field(None, description="Email for completion notification")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for completion notification")

    # Voice settings
    stability: float = Field(0.6, ge=0.0, le=1.0, description="Voice stability (0.0-1.0)")
    similarity_boost: float = Field(0.8, ge=0.0, le=1.0, description="Similarity boost (0.0-1.0)")

    @validator('voice_name')
    def validate_voice_name(cls, v):
        """Validate voice name"""
        if not v.strip():
            raise ValueError('Voice name cannot be empty')
        return v.strip()

    @validator('text')
    def validate_text(cls, v):
        """Validate text content"""
        if not v.strip():
            raise ValueError('Text cannot be empty')
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "voice_name": "My Voice Clone",
                "text": "Hello, this is a test of my cloned voice speaking in multiple languages.",
                "description": "Personal voice clone for multilingual content",
                "model": "eleven_multilingual_v2",
                "notification_email": "user@example.com",
                "webhook_url": "https://api.example.com/voice-ready",
                "stability": 0.6,
                "similarity_boost": 0.8
            }
        }


class VoiceCleanupRequest(BaseModel):
    """Request model for voice cleanup operations"""

    cleanup_type: str = Field("oldest", description="Cleanup type: 'oldest', 'all', 'specific'")
    voice_ids: Optional[List[str]] = Field(None, description="Specific voice IDs to delete (for 'specific' type)")
    max_voices: Optional[int] = Field(5, ge=1, le=50, description="Maximum number of voices to keep")

    @validator('cleanup_type')
    def validate_cleanup_type(cls, v):
        """Validate cleanup type"""
        allowed_types = ['oldest', 'all', 'specific']
        if v not in allowed_types:
            raise ValueError(f'Cleanup type must be one of: {allowed_types}')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "cleanup_type": "oldest",
                "max_voices": 5
            }
        }


class JobStatusRequest(BaseModel):
    """Request model for job status queries"""

    include_details: bool = Field(False, description="Include detailed job information")
    include_logs: bool = Field(False, description="Include job execution logs")

    class Config:
        json_schema_extra = {
            "example": {
                "include_details": True,
                "include_logs": False
            }
        }


class HealthCheckRequest(BaseModel):
    """Request model for health check"""

    check_dependencies: bool = Field(True, description="Check external dependencies")
    check_queue: bool = Field(True, description="Check queue system health")

    class Config:
        json_schema_extra = {
            "example": {
                "check_dependencies": True,
                "check_queue": True
            }
        }


class NotificationRequest(BaseModel):
    """Request model for testing notifications"""

    notification_type: str = Field(..., description="Notification type: 'email' or 'webhook'")
    recipient: str = Field(..., description="Email address or webhook URL")
    test_data: Dict[str, Any] = Field(default_factory=dict, description="Test data for notification")

    @validator('notification_type')
    def validate_notification_type(cls, v):
        """Validate notification type"""
        allowed_types = ['email', 'webhook']
        if v not in allowed_types:
            raise ValueError(f'Notification type must be one of: {allowed_types}')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "notification_type": "email",
                "recipient": "test@example.com",
                "test_data": {
                    "job_id": "test-job-123",
                    "voice_name": "Test Voice"
                }
            }
        }