"""
Pydantic models for API responses
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class BaseResponse(BaseModel):
    """Base response model with proper JSON serialization"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VoiceCloneResponse(BaseResponse):
    """Response model for voice cloning job submission"""

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    message: str = Field(..., description="Status message")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Job creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "vcj_abc123def456",
                "status": "pending",
                "message": "Voice cloning job submitted successfully",
                "estimated_completion": "2025-01-15T10:30:00Z",
                "created_at": "2025-01-15T10:25:00Z"
            }
        }


class JobStatusResponse(BaseResponse):
    """Response model for job status queries"""

    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Current job status")
    progress: int = Field(0, ge=0, le=100, description="Job progress percentage")
    message: str = Field(..., description="Current status message")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")

    # Optional detailed information
    voice_id: Optional[str] = Field(None, description="Created voice ID (if completed)")
    voice_name: Optional[str] = Field(None, description="Voice name")
    output_file: Optional[str] = Field(None, description="Generated audio file path")
    file_size: Optional[int] = Field(None, description="Output file size in bytes")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")

    # Error information
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(0, description="Number of retry attempts")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "vcj_abc123def456",
                "status": "completed",
                "progress": 100,
                "message": "Voice cloning completed successfully",
                "created_at": "2025-01-15T10:25:00Z",
                "updated_at": "2025-01-15T10:28:45Z",
                "completed_at": "2025-01-15T10:28:45Z",
                "voice_id": "v_xyz789",
                "voice_name": "My Voice Clone",
                "output_file": "output/vcj_abc123def456.mp3",
                "file_size": 524288,
                "duration": 12.5,
                "retry_count": 0
            }
        }


class VoiceInfo(BaseModel):
    """Model for voice information"""

    voice_id: str = Field(..., description="Voice identifier")
    name: str = Field(..., description="Voice name")
    category: str = Field(..., description="Voice category (premade, cloned, generated)")
    description: Optional[str] = Field(None, description="Voice description")
    created_at: Optional[str] = Field(None, description="Creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "voice_id": "v_abc123",
                "name": "My Voice Clone",
                "category": "cloned",
                "description": "Personal voice clone for content creation",
                "created_at": "2025-01-15T10:20:00Z"
            }
        }


class VoiceListResponse(BaseModel):
    """Response model for voice listing"""

    total_voices: int = Field(..., description="Total number of voices")
    custom_voices: int = Field(..., description="Number of custom voices")
    premade_voices: int = Field(..., description="Number of premade voices")
    voices: List[VoiceInfo] = Field(..., description="List of voice information")

    class Config:
        json_schema_extra = {
            "example": {
                "total_voices": 25,
                "custom_voices": 3,
                "premade_voices": 22,
                "voices": [
                    {
                        "voice_id": "v_abc123",
                        "name": "My Voice Clone",
                        "category": "cloned",
                        "description": "Personal voice clone",
                        "created_at": "2025-01-15T10:20:00Z"
                    }
                ]
            }
        }


class VoiceCleanupResponse(BaseModel):
    """Response model for voice cleanup operations"""

    success: bool = Field(..., description="Cleanup operation success status")
    message: str = Field(..., description="Operation result message")
    deleted_voices: int = Field(0, description="Number of voices deleted")
    remaining_voices: int = Field(..., description="Number of voices remaining")
    deleted_voice_ids: List[str] = Field(default_factory=list, description="IDs of deleted voices")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Successfully deleted 2 oldest voices",
                "deleted_voices": 2,
                "remaining_voices": 8,
                "deleted_voice_ids": ["v_old123", "v_old456"]
            }
        }


class HealthCheckResponse(BaseModel):
    """Response model for health check"""

    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    version: str = Field(..., description="Service version")
    uptime: float = Field(..., description="Service uptime in seconds")

    # Component health
    elevenlabs_api: str = Field(..., description="ElevenLabs API status")
    queue_system: str = Field(..., description="Queue system status")
    file_system: str = Field(..., description="File system status")

    # Metrics
    total_jobs: int = Field(0, description="Total jobs processed")
    active_jobs: int = Field(0, description="Currently active jobs")
    failed_jobs: int = Field(0, description="Failed jobs count")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-01-15T10:30:00Z",
                "version": "1.0.0",
                "uptime": 3600.5,
                "elevenlabs_api": "connected",
                "queue_system": "running",
                "file_system": "available",
                "total_jobs": 150,
                "active_jobs": 2,
                "failed_jobs": 5
            }
        }


class ErrorResponse(BaseResponse):
    """Standard error response model"""

    error: bool = Field(True, description="Indicates this is an error response")
    message: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code for programmatic handling")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "error": True,
                "message": "Voice cloning failed due to invalid audio format",
                "error_code": "INVALID_AUDIO_FORMAT",
                "details": {
                    "supported_formats": [".wav", ".mp3"],
                    "received_format": ".flac"
                },
                "timestamp": "2025-01-15T10:30:00Z"
            }
        }


class NotificationResponse(BaseModel):
    """Response model for notification operations"""

    success: bool = Field(..., description="Notification delivery success status")
    notification_type: str = Field(..., description="Type of notification sent")
    recipient: str = Field(..., description="Notification recipient")
    message: str = Field(..., description="Result message")
    sent_at: datetime = Field(default_factory=datetime.utcnow, description="Notification sent timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "notification_type": "email",
                "recipient": "user@example.com",
                "message": "Email notification sent successfully",
                "sent_at": "2025-01-15T10:30:00Z"
            }
        }