# ElevenLabs Voice Cloning Service

A professional FastAPI-based microservice for voice cloning using ElevenLabs API with async job processing, queue management, and comprehensive notification system.

## Features

### Core Functionality
- ✅ **Voice Cloning**: Upload WAV/MP3 files to create voice clones
- ✅ **Speech Synthesis**: Generate MP3 audio with cloned voices
- ✅ **Multi-language Support**: Dutch and 32+ languages via ElevenLabs with various models (v2, v3, Flash, Turbo)
- ✅ **Voice Limit Management**: Automatic cleanup of oldest voices when limit reached
- ✅ **Endless Loop Prevention**: Max retry limits to prevent infinite cleanup attempts

### Professional Architecture
- ✅ **FastAPI Web Service**: RESTful API with OpenAPI documentation
- ✅ **Async Job Queue**: Background processing with Redis support
- ✅ **Notification System**: Mock email and webhook notifications
- ✅ **File Management**: Professional file handling and cleanup utilities
- ✅ **Error Handling**: Comprehensive error handling and logging
- ✅ **Health Monitoring**: System health checks and metrics

### Clean Dependencies
- ✅ **Minimal Requirements**: Only essential packages, removed OpenVoice dependencies
- ✅ **Production Ready**: Professional logging, monitoring, and deployment support

## Quick Start

### Prerequisites
- Python 3.8+
- ElevenLabs API key (Starter plan or higher)

### Installation

1. **Clone and setup**:
```bash
cd fastapi_elevenlabs_service
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
# Copy .env file and update your API key
cp .env.example .env
# Edit .env file with your ELEVENLABS_API_KEY
```

3. **Run the service**:
```bash
python main.py
```

The service will start on `http://localhost:8000`

### API Documentation
- **OpenAPI Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Voice Cloning
- `POST /clone-voice` - Submit voice cloning job
- `GET /job/{job_id}/status` - Check job status
- `GET /job/{job_id}/download` - Download generated MP3

### Voice Management
- `GET /voices/list` - List all voices
- `DELETE /voices/cleanup` - Clean up old voices

### System
- `GET /health` - System health check
- `POST /test/notification` - Test notifications

## Usage Examples

### 1. Clone Voice and Generate Speech

```bash
# Upload audio files and create voice clone
curl -X POST "http://localhost:8000/clone-voice" \
  -F "files=@marjorie1.mp3" \
  -F "files=@marjorie2.mp3" \
  -F "files=@marjorie3.mp3" \
  -F "voice_name=Marjorie Clone" \
  -F "text=Ik ben Marjorie van Waveren uit Schagen. Jarenlang werkte ik bij de ING Bank." \
  -F "notification_email=user@example.com"
```

Response:
```json
{
  "job_id": "vcj_20250115_143022_3f",
  "status": "pending",
  "message": "Voice cloning job submitted successfully",
  "estimated_completion": "2025-01-15T14:35:22Z",
  "created_at": "2025-01-15T14:30:22Z"
}
```

### 2. Check Job Status

```bash
curl "http://localhost:8000/job/vcj_20250115_143022_3f/status?include_details=true"
```

Response:
```json
{
  "job_id": "vcj_20250115_143022_3f",
  "status": "completed",
  "progress": 100,
  "message": "Voice cloning completed successfully",
  "voice_id": "v_abc123",
  "voice_name": "Marjorie Clone",
  "output_file": "output/vcj_20250115_143022_3f_marjorie_clone_20250115_143045.mp3",
  "file_size": 245760
}
```

### 3. Download Generated Audio

```bash
curl -O "http://localhost:8000/job/vcj_20250115_143022_3f/download"
```

### 4. Voice Management

```bash
# List all voices
curl "http://localhost:8000/voices/list"

# Clean up oldest voices (keep 5 newest)
curl -X DELETE "http://localhost:8000/voices/cleanup" \
  -H "Content-Type: application/json" \
  -d '{"cleanup_type": "oldest", "max_voices": 5}'
```

## Configuration

### Environment Variables (.env)

```env
# ElevenLabs API
ELEVENLABS_API_KEY=your_api_key_here

# Service Settings
DEBUG=true
MAX_FILE_SIZE_MB=50
MAX_CONCURRENT_JOBS=5

# Voice Management
MAX_VOICE_RETRIES=3
VOICE_CLEANUP_ENABLED=true

# Notifications
MOCK_EMAIL_ENABLED=true
MOCK_WEBHOOK_ENABLED=true
```

## Architecture

```
fastapi_elevenlabs_service/
├── main.py                 # FastAPI application
├── config/
│   └── settings.py         # Configuration management
├── models/
│   ├── requests.py         # Pydantic request models
│   └── responses.py        # Pydantic response models
├── services/
│   ├── voice_cloning.py    # Core cloning logic
│   ├── queue_manager.py    # Job queue management
│   └── notifications.py    # Email/webhook mocks
├── utils/
│   ├── elevenlabs_client.py # ElevenLabs API client
│   └── file_manager.py     # File operations
└── output/                 # Generated MP3 files
```

## Key Features Detail

### Voice Limit Management
- Automatically detects when ElevenLabs voice limit is reached
- Deletes oldest custom voices to make room for new clones
- Prevents endless loops with configurable retry limits
- Safe cleanup with error handling

### Async Job Processing
- Background processing of voice cloning jobs
- Real-time progress updates
- Comprehensive job status tracking
- Error handling and retry mechanisms

### Professional File Management
- Secure file upload and validation
- Automatic cleanup of temporary files
- Organized output directory structure
- File size and format validation

### Mock Notification System
- Email notifications for job completion/failure
- Webhook notifications for system integration
- Configurable notification preferences
- Development-friendly mock implementations

## Troubleshooting

### Common Issues

1. **API Key Errors**:
   - Ensure your ElevenLabs API key has voice cloning permissions
   - Regenerate API key if permissions are missing

2. **Voice Limit Reached**:
   - Service automatically handles this by deleting oldest voices
   - Manually clean up voices using `/voices/cleanup` endpoint

3. **File Upload Issues**:
   - Check file format (only WAV/MP3 supported)
   - Verify file size is under limit (default 50MB)
   - Ensure files are valid audio format

4. **Job Processing Failures**:
   - Check `/health` endpoint for system status
   - Review logs for specific error messages
   - Ensure ElevenLabs API is accessible

### Health Check
Monitor service health at `/health` endpoint:
- Overall system status
- ElevenLabs API connectivity
- Queue system status
- File system availability
- Job processing metrics

## Production Deployment

For production deployment:
1. Set `DEBUG=false` in .env
2. Configure proper CORS origins
3. Set up Redis for queue backend
4. Implement proper logging and monitoring
5. Configure file cleanup schedules
6. Set up SSL/HTTPS
7. Configure rate limiting

## License

This is a professional voice cloning service implementation. Ensure compliance with ElevenLabs terms of service and voice cloning regulations.