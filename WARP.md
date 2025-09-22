# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a Python FastAPI microservice for voice cloning using ElevenLabs API, built for MyMemori.es. It enables family memory preservation by allowing users to clone voices and generate speech in their own voice from uploaded audio samples.

The repository contains two main components:
- **OpenVoice**: Original MyShell voice cloning library (research/base implementation)
- **fastapi_elevenlabs_service**: Production FastAPI microservice (primary focus)

## Key Commands

### Environment Setup
```powershell
# Install dependencies
pip install -r requirements.txt
pip install -r fastapi_elevenlabs_service\requirements.txt

# Setup environment file
copy .env.example .env
# Edit .env with your ELEVENLABS_API_KEY and other settings
```

### Development Server
```powershell
# Start the development server
cd fastapi_elevenlabs_service
python main.py
# Server runs on http://localhost:8000

# Alternative with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Testing
```powershell
# Run comprehensive test suite
cd fastapi_elevenlabs_service
python test_service.py

# Test individual endpoints
curl http://localhost:8000/health
curl http://localhost:8000/voices/list
```

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Architecture Overview

### Core Service Structure
The main service is located in `fastapi_elevenlabs_service/` with this architecture:

```
fastapi_elevenlabs_service/
├── main.py                 # FastAPI application entry point
├── config/
│   └── settings.py         # Environment-based configuration
├── models/
│   ├── requests.py         # Pydantic request models
│   └── responses.py        # Pydantic response models  
├── services/
│   ├── voice_cloning.py    # Core voice cloning logic
│   ├── queue_manager.py    # Async job queue management
│   └── notifications.py    # Email/webhook notifications
├── utils/
│   ├── elevenlabs_client.py # ElevenLabs API client
│   └── file_manager.py     # File operations & cleanup
└── output/                 # Generated audio files
```

### Key Service Components

**VoiceCloningService** (`services/voice_cloning.py`):
- End-to-end voice cloning workflow
- Handles ElevenLabs voice limits with automatic cleanup
- Text chunking for long content (model-specific limits)
- Progress tracking and error handling

**ElevenLabsClient** (`utils/elevenlabs_client.py`):
- Direct ElevenLabs API integration
- Voice management (create, list, delete)
- Speech generation with settings control
- Rate limiting and error handling

**QueueManager** (`services/queue_manager.py`):
- Async background job processing
- Job status tracking and progress updates
- Retry mechanisms for failed jobs

### Configuration Management
Settings are managed via Pydantic in `config/settings.py` with environment variable support:
- ElevenLabs API configuration
- File size and format limits
- Voice management settings
- Queue and notification configuration

## Development Workflow

### Primary Endpoints
- `POST /clone-voice` - Submit voice cloning job with audio files
- `GET /job/{job_id}/status` - Check job progress
- `GET /job/{job_id}/download` - Download generated audio
- `GET /voices/list` - List all voices in account
- `DELETE /voices/cleanup` - Clean up old voices
- `GET /health` - System health check

### Voice Limit Management
The service automatically handles ElevenLabs voice limits:
- Detects when limit is reached during voice creation
- Automatically deletes oldest custom voices
- Configurable retry limits prevent infinite loops
- Safe cleanup with comprehensive error handling

### Text Chunking Strategy
Long text is automatically chunked based on model limitations:
- `eleven_multilingual_v2/v1/sts_v2`: 9,500 chars max
- `eleven_v3`: 2,800 chars max
- `eleven_flash_v2_5/turbo_v2_5/turbo_v2/flash_v2`: 4,500 chars max
- Smart splitting at paragraph/sentence boundaries
- Audio chunks concatenated into final output

### File Management
- Secure upload validation (WAV/MP3 only)
- Temporary file cleanup after job completion
- Organized output directory structure
- Configurable size limits (default 50MB)

## Important Environment Variables

```env
# Required
ELEVENLABS_API_KEY=your_api_key_here

# Service Configuration  
DEBUG=true
MAX_FILE_SIZE_MB=50
MAX_CONCURRENT_JOBS=5

# Voice Management
MAX_VOICE_RETRIES=3
VOICE_CLEANUP_ENABLED=true

# Notifications
MOCK_EMAIL_ENABLED=true
RESEND_API_KEY=your_resend_key_here
```

## Common Development Tasks

### Adding New Voice Models
1. Update model validation in `main.py` endpoint
2. Add model-specific chunk limits in `voice_cloning.py`
3. Update API documentation

### Extending Notification System
1. Implement new notification service in `services/notifications.py`
2. Add configuration in `settings.py`
3. Register in notification manager

### Testing Voice Cloning
Use the comprehensive test suite in `test_service.py` which tests:
- App initialization and service health
- ElevenLabs API connectivity  
- Voice listing and management
- Job submission and status tracking
- Notification system functionality

## Troubleshooting

### Common Issues
- **Voice limit errors**: Service handles automatically via cleanup
- **File upload failures**: Check format (WAV/MP3) and size limits
- **Job processing errors**: Check `/health` endpoint for system status
- **API connectivity**: Verify `ELEVENLABS_API_KEY` and network access

### Monitoring
- Health checks at `/health` show system status
- Queue statistics available via health endpoint
- Comprehensive logging for debugging
- Progress tracking for long-running jobs

## Dependencies

### Core Requirements
- Python 3.8+
- FastAPI for web service
- ElevenLabs API (Starter plan+ for voice cloning)
- Pydantic for data validation
- asyncio for concurrent processing

### Optional Dependencies
- Redis for production queue backend
- Resend for email notifications
- pydub for audio processing
