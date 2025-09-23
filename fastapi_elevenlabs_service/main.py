"""
FastAPI application for ElevenLabs Voice Cloning Service
Professional web service with async queue processing and comprehensive API
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import List, Dict, Any, Optional
import logging
import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path

# Internal imports
from config.settings import get_settings
from models.requests import (VoiceCloneRequest, VoiceCleanupRequest, JobStatusRequest,
                           HealthCheckRequest, NotificationRequest)
from models.responses import (VoiceCloneResponse, JobStatusResponse, VoiceListResponse,
                            VoiceCleanupResponse, HealthCheckResponse, ErrorResponse,
                            NotificationResponse, JobStatus)
from services.voice_cloning import get_voice_cloning_service
from services.queue_manager import get_queue_manager
from services.notifications import get_notification_manager
from utils.file_manager import get_file_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get global instances
settings = get_settings()
voice_service = get_voice_cloning_service()
queue_manager = get_queue_manager()
notification_manager = get_notification_manager()
file_manager = get_file_manager()

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="MyMemori.es Personal Story Service - Create stories in your own voice using advanced AI",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store app startup time for health checks
app_start_time = datetime.utcnow()


# Dependency injection
async def get_current_settings():
    """Get current application settings"""
    return settings


# Startup/shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    try:
        # Register voice cloning processor
        queue_manager.register_processor("voice_cloning", voice_service.process_voice_cloning_job)

        # Start queue workers
        await queue_manager.start_workers()

        logger.info("Application startup completed successfully")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger.info("Shutting down application")

    try:
        # Stop queue workers
        await queue_manager.stop_workers()

        # Cleanup temporary files
        file_manager.cleanup_old_files(max_age_hours=1)

        logger.info("Application shutdown completed")

    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    error_response = ErrorResponse(
        message=exc.detail,
        error_code=f"HTTP_{exc.status_code}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    error_response = ErrorResponse(
        message="Internal server error",
        error_code="INTERNAL_ERROR"
    )
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(mode='json')
    )


# API Endpoints

@app.post("/clone-voice", response_model=VoiceCloneResponse, tags=["Story Creation"])
async def clone_voice(
    files: List[UploadFile] = File(..., description="Audio files to create your personal voice"),
    voice_name: str = "My Personal Story",
    text: str = "Hello, this is my story speaking in my own voice.",
    model: str = "eleven_multilingual_v2",
    description: Optional[str] = None,
    notification_email: Optional[str] = None,
    webhook_url: Optional[str] = None,
    stability: float = 0.6,
    similarity_boost: float = 0.8,
    style: float = 0.1
):
    """
    Create a personal story in your own voice

    This endpoint accepts multiple audio recordings, creates your personal voice,
    and generates a spoken story with the text you provide.
    Perfect for preserving memories and sharing stories with family.
    """
    try:
        # Validate request
        if not files:
            raise HTTPException(status_code=400, detail="No audio files provided")

        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")

        # Valid ElevenLabs models (as of current API)
        valid_models = [
            "eleven_multilingual_v2",
            "eleven_v3", 
            "eleven_flash_v2_5",
            "eleven_turbo_v2_5",
            "eleven_turbo_v2",
            "eleven_flash_v2",
            "eleven_english_sts_v2",
            "eleven_monolingual_v1",
            "eleven_multilingual_v1",
            "eleven_multilingual_sts_v2"
        ]
        
        if model not in valid_models:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid model '{model}'. Supported models: {', '.join(valid_models)}"
            )
        
        # Model-specific text length validation
        if model == "eleven_v3" and len(text) > 3000:
            raise HTTPException(status_code=400, detail="Text too long for v3 model (max 3000 characters)")
        elif model in ["eleven_multilingual_v2", "eleven_multilingual_v1", "eleven_multilingual_sts_v2"] and len(text) > 10000:
            raise HTTPException(status_code=400, detail="Text too long for multilingual model (max 10000 characters)")
        elif model in ["eleven_flash_v2_5", "eleven_turbo_v2_5", "eleven_turbo_v2", "eleven_flash_v2"] and len(text) > 5000:
            raise HTTPException(status_code=400, detail="Text too long for flash/turbo model (max 5000 characters)")

        # Create job ID and save uploaded files
        job_id = f"vcj_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(files)}"
        audio_file_paths = []

        for file in files:
            # Validate file
            if not file.filename:
                continue

            file_extension = Path(file.filename).suffix.lower()
            if file_extension not in settings.allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file format: {file_extension}. Allowed: {settings.allowed_extensions}"
                )

            # Read file content
            file_content = await file.read()

            if len(file_content) > settings.max_file_size_mb * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large: {file.filename} (max {settings.max_file_size_mb}MB)"
                )

            # Save file
            saved_path = file_manager.save_uploaded_file(file_content, file.filename, job_id)
            if saved_path:
                audio_file_paths.append(saved_path)

        if not audio_file_paths:
            raise HTTPException(status_code=400, detail="No valid audio files")

        # Prepare job data
        job_data = {
            "audio_files": audio_file_paths,
            "voice_name": voice_name.strip(),
            "text": text.strip(),
            "model": model,
            "description": description,
            "notification_email": notification_email,
            "webhook_url": webhook_url,
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style
        }

        # Submit job to queue
        job_id = await queue_manager.submit_job("voice_cloning", job_data)

        # Estimate completion time based on model
        minutes = 25 if model == "eleven_v3" else 15

        return VoiceCloneResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message="Your personal story is being created! You'll receive an email when it's ready.",
            estimated_completion=datetime.utcnow() + timedelta(minutes=minutes)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in clone_voice endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/job/{job_id}/status", response_model=JobStatusResponse, tags=["Story Management"])
async def get_job_status(
    job_id: str,
    include_details: bool = False,
    include_logs: bool = False
):
    """
    Check the progress of your personal story creation

    Returns detailed information about your story progress, completion status,
    and any messages.
    """
    try:
        job_status = await queue_manager.get_job_status(job_id)

        if not job_status:
            raise HTTPException(status_code=404, detail="Job not found")

        # Convert to response model
        response_data = {
            "job_id": job_id,
            "status": job_status["status"],
            "progress": job_status.get("progress", 0),
            "message": job_status.get("data", {}).get("message", "Processing"),
            "created_at": datetime.fromisoformat(job_status["created_at"]),
            "updated_at": datetime.fromisoformat(job_status["updated_at"]),
            "retry_count": job_status.get("retry_count", 0)
        }

        # Add completion time if job is done
        if job_status.get("completed_at"):
            response_data["completed_at"] = datetime.fromisoformat(job_status["completed_at"])

        # Add error information if job failed
        if job_status.get("error_message"):
            response_data["error_message"] = job_status["error_message"]

        # Add detailed information if requested
        if include_details and job_status.get("result"):
            result = job_status["result"]
            response_data.update({
                "voice_id": result.get("voice_id"),
                "voice_name": result.get("voice_name"),
                "output_file": result.get("output_file"),
                "file_size": result.get("file_size"),
                "duration": result.get("duration")
            })

        return JobStatusResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/job/{job_id}/download", tags=["Story Management"])
async def download_job_result(job_id: str):
    """
    Download your completed personal story

    Returns your story as an MP3 audio file that you can save and share.
    """
    try:
        job_status = await queue_manager.get_job_status(job_id)

        if not job_status:
            raise HTTPException(status_code=404, detail="Job not found")

        if job_status["status"] != JobStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Job not completed yet")

        # Get output file path
        result = job_status.get("result")
        if not result or not result.get("output_file"):
            raise HTTPException(status_code=404, detail="Output file not found")

        output_file = result["output_file"]
        output_path = Path(output_file)

        if not output_path.exists():
            raise HTTPException(status_code=404, detail="Output file no longer exists")

        # Return file as download
        voice_name = result.get("voice_name", "voice_clone")
        safe_filename = file_manager._sanitize_filename(voice_name) + ".mp3"

        return FileResponse(
            path=output_path,
            filename=safe_filename,
            media_type="audio/mpeg"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading job result for {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/voices/list", response_model=VoiceListResponse, tags=["Voice Management"])
async def list_voices():
    """
    List all voices in the ElevenLabs account

    Returns information about premade and custom voices.
    """
    try:
        voices = await voice_service.list_voices()

        # Categorize voices
        custom_voices = [v for v in voices if v.get("category") in ["cloned", "generated"]]
        premade_voices = [v for v in voices if v.get("category") == "premade"]

        return VoiceListResponse(
            total_voices=len(voices),
            custom_voices=len(custom_voices),
            premade_voices=len(premade_voices),
            voices=[
                {
                    "voice_id": v["voice_id"],
                    "name": v["name"],
                    "category": v.get("category", "unknown"),
                    "description": v.get("description"),
                    "created_at": v.get("created_at")
                }
                for v in voices
            ]
        )

    except Exception as e:
        logger.error(f"Error listing voices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/voices/cleanup", response_model=VoiceCleanupResponse, tags=["Voice Management"])
async def cleanup_voices(request: VoiceCleanupRequest):
    """
    Clean up custom voices to free up space

    Supports different cleanup strategies like deleting oldest voices
    or removing all custom voices.
    """
    try:
        result = await voice_service.cleanup_voices(
            cleanup_type=request.cleanup_type,
            max_voices=request.max_voices
        )

        return VoiceCleanupResponse(**result)

    except Exception as e:
        logger.error(f"Error cleaning up voices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthCheckResponse, tags=["System"])
async def health_check(request: HealthCheckRequest = Depends()):
    """
    System health check endpoint

    Returns information about service health, dependencies,
    and operational metrics.
    """
    try:
        # Calculate uptime
        uptime = (datetime.utcnow() - app_start_time).total_seconds()

        # Get queue statistics
        queue_stats = await queue_manager.get_queue_stats()

        # Check ElevenLabs API (basic connectivity)
        elevenlabs_status = "connected"
        try:
            await voice_service.list_voices()
        except Exception:
            elevenlabs_status = "error"

        # File system check
        file_system_status = "available"
        try:
            file_manager.get_directory_stats()
        except Exception:
            file_system_status = "error"

        # Overall status
        overall_status = "healthy"
        if elevenlabs_status == "error" or file_system_status == "error":
            overall_status = "degraded"

        return HealthCheckResponse(
            status=overall_status,
            version=settings.app_version,
            uptime=uptime,
            elevenlabs_api=elevenlabs_status,
            queue_system="running",
            file_system=file_system_status,
            total_jobs=queue_stats.get("total_jobs", 0),
            active_jobs=queue_stats.get("active_jobs", 0),
            failed_jobs=queue_stats.get("failed_jobs", 0)
        )

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthCheckResponse(
            status="error",
            version=settings.app_version,
            uptime=0,
            elevenlabs_api="error",
            queue_system="error",
            file_system="error",
            total_jobs=0,
            active_jobs=0,
            failed_jobs=0
        )


@app.post("/test/notification", response_model=NotificationResponse, tags=["Testing"])
async def test_notification(request: NotificationRequest):
    """
    Test notification delivery (development/testing endpoint)

    Allows testing of email and webhook notifications without
    running a full voice cloning job.
    """
    try:
        test_data = {
            "job_id": request.test_data.get("job_id", "test-123"),
            "voice_name": request.test_data.get("voice_name", "Test Voice"),
            "status": "completed",
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat()
        }

        if request.notification_type == "email":
            success = await notification_manager.email_service.send_completion_email(
                request.recipient, test_data
            )
            message = "Test email sent successfully" if success else "Failed to send test email"

        elif request.notification_type == "webhook":
            success = await notification_manager.webhook_service.send_completion_webhook(
                request.recipient, test_data
            )
            message = "Test webhook sent successfully" if success else "Failed to send test webhook"

        else:
            raise HTTPException(status_code=400, detail="Invalid notification type")

        return NotificationResponse(
            success=success,
            notification_type=request.notification_type,
            recipient=request.recipient,
            message=message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test notification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Development server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )