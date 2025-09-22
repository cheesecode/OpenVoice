"""
Core voice cloning service with ElevenLabs integration and limit management
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from utils.elevenlabs_client import ElevenLabsClient
from utils.file_manager import get_file_manager
from services.notifications import get_notification_manager
from services.queue_manager import QueueJob
from models.responses import JobStatus
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
file_manager = get_file_manager()
notification_manager = get_notification_manager()


class VoiceCloningService:
    """Professional voice cloning service with comprehensive error handling"""

    def __init__(self):
        self.client = ElevenLabsClient()

    async def process_voice_cloning_job(self, job: QueueJob) -> Dict[str, Any]:
        """
        Process a voice cloning job end-to-end

        Args:
            job: Queue job with cloning parameters

        Returns:
            Dictionary with job result information
        """
        job_data = job.data
        job_id = job.job_id

        try:
            logger.info(f"Starting voice cloning job: {job_id}")

            # Extract job parameters
            audio_files = job_data.get("audio_files", [])
            voice_name = job_data.get("voice_name", "Unnamed Voice")
            text = job_data.get("text", "")
            model = job_data.get("model", "eleven_multilingual_v2")
            description = job_data.get("description")
            notification_email = job_data.get("notification_email")
            webhook_url = job_data.get("webhook_url")
            stability = job_data.get("stability", 0.6)
            similarity_boost = job_data.get("similarity_boost", 0.8)

            # Step 1: Validate audio files (10% progress)
            await self._update_job_progress(job_id, 10, "Validating audio files")

            valid_files, validation_errors = file_manager.validate_audio_files(audio_files)
            if not valid_files:
                raise ValueError(f"No valid audio files: {'; '.join(validation_errors)}")

            logger.info(f"Validated {len(valid_files)} audio files for job {job_id}")

            # Step 2: Ensure voice capacity (20% progress)
            await self._update_job_progress(job_id, 20, "Checking voice capacity")

            if not await self._ensure_voice_capacity_with_retry(job_id):
                raise Exception("Failed to ensure voice capacity after maximum retries")

            # Step 3: Create voice clone (50% progress)
            await self._update_job_progress(job_id, 50, "Creating voice clone")

            voice_id = await self._create_voice_clone_safe(valid_files, voice_name, description, job_id)
            if not voice_id:
                raise Exception("Failed to create voice clone - this may be due to voice limits, audio quality, or API quota issues")

            logger.info(f"Created voice clone {voice_id} for job {job_id}")

            # Step 4: Generate speech with chunking (75% progress)
            await self._update_job_progress(job_id, 75, "Generating speech with chunking")

            audio_data = await self._generate_chunked_speech(voice_id, text, model, job_id, stability, similarity_boost)
            if not audio_data:
                raise Exception("Failed to generate speech")

            # Step 5: Save output file (90% progress)
            await self._update_job_progress(job_id, 90, "Saving output file")

            output_file = file_manager.save_generated_audio(audio_data, job_id, voice_name)
            if not output_file:
                raise Exception("Failed to save generated audio")

            # Step 6: Send notifications (95% progress)
            await self._update_job_progress(job_id, 95, "Sending notifications")

            # Prepare result data
            result = {
                "voice_id": voice_id,
                "voice_name": voice_name,
                "output_file": output_file,
                "file_size": len(audio_data),
                "text": text,
                "created_at": job.created_at.isoformat(),
                "completed_at": datetime.utcnow().isoformat()
            }

            # Send completion notifications
            await self._send_completion_notifications(
                result, notification_email, webhook_url, job_id
            )

            # Cleanup temporary files
            file_manager.cleanup_temp_files(job_id)

            logger.info(f"Voice cloning job completed successfully: {job_id}")
            return result

        except Exception as e:
            error_message = str(e)
            logger.error(f"Voice cloning job failed: {job_id} - {error_message}")

            # Send failure notifications
            await self._send_failure_notifications(
                job_data, error_message, notification_email, webhook_url, job_id
            )

            # Cleanup temporary files
            file_manager.cleanup_temp_files(job_id)

            raise e

    async def _ensure_voice_capacity_with_retry(self, job_id: str, max_retries: int = None) -> bool:
        """
        Ensure voice capacity with retry mechanism to prevent endless loops

        Args:
            job_id: Job identifier for logging
            max_retries: Maximum retry attempts (uses settings default if None)

        Returns:
            True if capacity is available, False if failed after retries
        """
        max_retries = max_retries or settings.max_voice_retries

        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Checking voice capacity for job {job_id} (attempt {attempt + 1}/{max_retries + 1})")

                # Use aggressive cleanup for the first attempt to free up more slots
                if attempt == 0:
                    if self.client.ensure_voice_capacity_aggressive(target_free_slots=2):
                        logger.info(f"Voice capacity available for job {job_id}")
                        return True
                else:
                    # Fall back to regular cleanup for retries
                    if self.client.ensure_voice_capacity():
                        logger.info(f"Voice capacity available for job {job_id}")
                        return True

                if attempt < max_retries:
                    logger.warning(f"Voice capacity check failed for job {job_id}, retrying...")
                    # Brief delay between retries
                    await asyncio.sleep(1.0)

            except Exception as e:
                logger.error(f"Voice capacity check error for job {job_id} (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(2.0)  # Longer delay on error

        logger.error(f"Failed to ensure voice capacity for job {job_id} after {max_retries + 1} attempts")
        return False

    async def _create_voice_clone_safe(self, audio_files: List[str], voice_name: str,
                                     description: str, job_id: str) -> Optional[str]:
        """
        Safely create voice clone with error handling

        Args:
            audio_files: List of valid audio file paths
            voice_name: Name for the voice clone
            description: Voice description
            job_id: Job identifier for logging

        Returns:
            Voice ID if successful, None if failed
        """
        try:
            # Run the potentially blocking operation in executor
            loop = asyncio.get_event_loop()
            voice_id = await loop.run_in_executor(
                None,
                self.client.create_voice_clone,
                audio_files,
                voice_name,
                description
            )

            if voice_id:
                logger.info(f"Voice clone created successfully for job {job_id}: {voice_id}")
            else:
                logger.error(f"Voice clone creation returned None for job {job_id}")

            return voice_id

        except Exception as e:
            logger.error(f"Exception in voice clone creation for job {job_id}: {e}")
            return None

    def _chunk_text(self, text: str, model: str) -> List[str]:
        """
        Split text into chunks based on model limitations

        Args:
            text: Full text to chunk
            model: ElevenLabs model name

        Returns:
            List of text chunks
        """
        # Model-specific chunk sizes (with safety margin)
        chunk_limits = {
            "eleven_multilingual_v2": 9500,
            "eleven_multilingual_v1": 9500,
            "eleven_multilingual_sts_v2": 9500,
            "eleven_v3": 2800,
            "eleven_flash_v2_5": 4500,
            "eleven_turbo_v2_5": 4500,
            "eleven_turbo_v2": 4500,
            "eleven_flash_v2": 4500,
            "eleven_english_sts_v2": 4500,
            "eleven_monolingual_v1": 4500
        }

        max_chunk_size = chunk_limits.get(model, 4500)

        # If text is short enough, return as single chunk
        if len(text) <= max_chunk_size:
            return [text]

        chunks = []
        remaining_text = text

        while remaining_text:
            if len(remaining_text) <= max_chunk_size:
                chunks.append(remaining_text)
                break

            # Find natural break point (paragraph, then sentence)
            chunk = remaining_text[:max_chunk_size]

            # Look for paragraph break (double newline)
            paragraph_break = chunk.rfind('\n\n')
            if paragraph_break > max_chunk_size * 0.7:  # If break is reasonable
                split_point = paragraph_break + 2
            else:
                # Look for sentence ending
                sentence_endings = ['. ', '! ', '? ']
                best_break = -1
                for ending in sentence_endings:
                    break_point = chunk.rfind(ending)
                    if break_point > max_chunk_size * 0.7:
                        best_break = max(best_break, break_point + len(ending))

                if best_break > 0:
                    split_point = best_break
                else:
                    # Last resort: break at word boundary
                    split_point = chunk.rfind(' ')
                    if split_point <= 0:
                        split_point = max_chunk_size

            chunks.append(remaining_text[:split_point].strip())
            remaining_text = remaining_text[split_point:].strip()

        logger.info(f"Split text into {len(chunks)} chunks for model {model}")
        return chunks

    async def _generate_chunked_speech(self, voice_id: str, text: str, model: str,
                                     job_id: str, stability: float, similarity_boost: float) -> Optional[bytes]:
        """
        Generate speech with text chunking and MP3 concatenation

        Args:
            voice_id: Voice identifier
            text: Full text to synthesize
            model: ElevenLabs model to use
            job_id: Job identifier for logging
            stability: Voice stability setting
            similarity_boost: Voice similarity boost setting

        Returns:
            Combined audio data bytes if successful, None if failed
        """
        try:
            # Split text into chunks
            text_chunks = self._chunk_text(text, model)

            if len(text_chunks) == 1:
                # Single chunk - use simple generation
                return await self._generate_speech_safe(voice_id, text, model, stability, similarity_boost, job_id)

            logger.info(f"Processing {len(text_chunks)} chunks for job {job_id}")

            # Generate audio for each chunk
            audio_chunks = []
            for i, chunk in enumerate(text_chunks):
                chunk_progress = 75 + (15 * i // len(text_chunks))  # Progress from 75% to 90%
                await self._update_job_progress(job_id, chunk_progress, f"Processing chunk {i+1}/{len(text_chunks)}")

                chunk_audio = await self._generate_speech_safe(voice_id, chunk, model, stability, similarity_boost, job_id)
                if not chunk_audio:
                    raise Exception(f"Failed to generate audio for chunk {i+1}")

                audio_chunks.append(chunk_audio)
                logger.info(f"Generated chunk {i+1}/{len(text_chunks)}: {len(chunk_audio)} bytes")

            # Concatenate audio chunks
            combined_audio = self._concatenate_audio_chunks(audio_chunks)
            logger.info(f"Combined {len(audio_chunks)} chunks into {len(combined_audio)} bytes")

            return combined_audio

        except Exception as e:
            logger.error(f"Failed to generate chunked speech for job {job_id}: {e}")
            return None

    def _concatenate_audio_chunks(self, audio_chunks: List[bytes]) -> bytes:
        """
        Simple MP3 concatenation by joining bytes
        For professional use, consider using proper audio processing libraries
        """
        # Simple concatenation - for MP3 this works for basic cases
        # In production, you might want to use pydub or similar for proper audio processing
        return b''.join(audio_chunks)

    async def _generate_speech_safe(self, voice_id: str, text: str, model: str,
                                  stability: float, similarity_boost: float, job_id: str) -> Optional[bytes]:
        """
        Safely generate speech with error handling

        Args:
            voice_id: Voice identifier
            text: Text to synthesize
            model: ElevenLabs model to use
            stability: Voice stability setting
            similarity_boost: Voice similarity boost setting
            job_id: Job identifier for logging

        Returns:
            Audio data bytes if successful, None if failed
        """
        try:
            # Run the potentially blocking operation in executor
            loop = asyncio.get_event_loop()
            audio_data = await loop.run_in_executor(
                None,
                self.client.generate_speech,
                voice_id,
                text,
                model,
                stability,
                similarity_boost
            )

            if audio_data:
                logger.info(f"Speech generated successfully for job {job_id}: {len(audio_data)} bytes")
            else:
                logger.error(f"Speech generation returned None for job {job_id}")

            return audio_data

        except Exception as e:
            logger.error(f"Exception in speech generation for job {job_id}: {e}")
            return None

    async def _update_job_progress(self, job_id: str, progress: int, message: str):
        """Update job progress through queue manager"""
        from services.queue_manager import get_queue_manager
        queue_manager = get_queue_manager()
        await queue_manager.update_job_progress(job_id, progress, message)

    async def _send_completion_notifications(self, result: Dict[str, Any],
                                           email: Optional[str], webhook_url: Optional[str],
                                           job_id: str):
        """Send completion notifications"""
        if email or webhook_url:
            try:
                notification_results = await notification_manager.notify_job_completion(
                    result, email, webhook_url
                )
                logger.info(f"Sent completion notifications for job {job_id}: {notification_results}")
            except Exception as e:
                logger.error(f"Failed to send completion notifications for job {job_id}: {e}")

    async def _send_failure_notifications(self, job_data: Dict[str, Any], error_message: str,
                                        email: Optional[str], webhook_url: Optional[str],
                                        job_id: str):
        """Send failure notifications"""
        if email or webhook_url:
            try:
                notification_results = await notification_manager.notify_job_failure(
                    job_data, error_message, email, webhook_url
                )
                logger.info(f"Sent failure notifications for job {job_id}: {notification_results}")
            except Exception as e:
                logger.error(f"Failed to send failure notifications for job {job_id}: {e}")

    async def list_voices(self) -> List[Dict[str, Any]]:
        """List all voices in the account"""
        try:
            loop = asyncio.get_event_loop()
            voices = await loop.run_in_executor(None, self.client.list_voices)
            return voices
        except Exception as e:
            logger.error(f"Failed to list voices: {e}")
            return []

    async def cleanup_voices(self, cleanup_type: str = "oldest",
                           max_voices: int = 5) -> Dict[str, Any]:
        """
        Clean up voices based on specified criteria

        Args:
            cleanup_type: Type of cleanup ("oldest", "all")
            max_voices: Maximum voices to keep (for "oldest" type)

        Returns:
            Cleanup result dictionary
        """
        try:
            loop = asyncio.get_event_loop()

            if cleanup_type == "oldest":
                # Keep only the newest voices, delete the rest
                custom_voices = await loop.run_in_executor(None, self.client.get_custom_voices)

                if len(custom_voices) <= max_voices:
                    return {
                        "success": True,
                        "message": f"No cleanup needed, only {len(custom_voices)} voices",
                        "deleted_voices": 0,
                        "remaining_voices": len(custom_voices)
                    }

                # Sort by creation time (oldest first)
                voices_to_delete = custom_voices[:len(custom_voices) - max_voices]
                deleted_count = 0
                deleted_ids = []

                for voice in voices_to_delete:
                    voice_id = voice["voice_id"]
                    if await loop.run_in_executor(None, self.client.delete_voice, voice_id):
                        deleted_count += 1
                        deleted_ids.append(voice_id)

                return {
                    "success": True,
                    "message": f"Deleted {deleted_count} oldest voices",
                    "deleted_voices": deleted_count,
                    "remaining_voices": len(custom_voices) - deleted_count,
                    "deleted_voice_ids": deleted_ids
                }

            elif cleanup_type == "all":
                # Delete all custom voices
                custom_voices = await loop.run_in_executor(None, self.client.get_custom_voices)
                deleted_count = 0
                deleted_ids = []

                for voice in custom_voices:
                    voice_id = voice["voice_id"]
                    if await loop.run_in_executor(None, self.client.delete_voice, voice_id):
                        deleted_count += 1
                        deleted_ids.append(voice_id)

                return {
                    "success": True,
                    "message": f"Deleted all {deleted_count} custom voices",
                    "deleted_voices": deleted_count,
                    "remaining_voices": 0,
                    "deleted_voice_ids": deleted_ids
                }

            else:
                return {
                    "success": False,
                    "message": f"Unknown cleanup type: {cleanup_type}",
                    "deleted_voices": 0,
                    "remaining_voices": 0
                }

        except Exception as e:
            logger.error(f"Voice cleanup failed: {e}")
            return {
                "success": False,
                "message": f"Cleanup failed: {str(e)}",
                "deleted_voices": 0,
                "remaining_voices": 0
            }


# Global voice cloning service instance
voice_cloning_service = VoiceCloningService()


def get_voice_cloning_service() -> VoiceCloningService:
    """Get global voice cloning service instance"""
    return voice_cloning_service