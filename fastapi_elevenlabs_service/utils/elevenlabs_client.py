"""
Direct ElevenLabs API client for voice cloning operations
"""

import requests
from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ElevenLabsClient:
    """Professional ElevenLabs API client with error handling"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.elevenlabs_api_key
        self.base_url = settings.elevenlabs_base_url
        self.headers = {"xi-api-key": self.api_key}

    def list_voices(self) -> List[Dict[str, Any]]:
        """List all voices in the account"""
        url = f"{self.base_url}/voices"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            voices_data = response.json()
            voices = voices_data.get('voices', [])

            logger.info(f"Retrieved {len(voices)} voices from ElevenLabs")
            return voices

        except requests.RequestException as e:
            logger.error(f"Failed to list voices: {e}")
            raise Exception(f"ElevenLabs API error: {e}")

    def get_custom_voices(self) -> List[Dict[str, Any]]:
        """Get all non-premade voices, prioritizing cloned voices for deletion"""
        all_voices = self.list_voices()
        
        # Filter out premade voices
        custom_voices = [
            voice for voice in all_voices
            if voice.get('category') != 'premade'
        ]
        
        # Sort by priority for deletion:
        # 1. Cloned voices first (easier to delete)
        # 2. Then by creation date (oldest first) if available
        def sort_key(voice):
            category = voice.get('category', '')
            # Prioritize cloned voices for deletion
            category_priority = 0 if category == 'cloned' else 1
            
            # Try to use date for secondary sorting, fallback to voice_id if no date
            date_str = voice.get('date_unix', voice.get('created_at', '0'))
            try:
                if isinstance(date_str, (int, float)):
                    date_value = int(date_str)
                elif isinstance(date_str, str) and date_str.isdigit():
                    date_value = int(date_str)
                else:
                    # Fallback to voice_id for consistent ordering
                    date_value = hash(voice.get('voice_id', '')) % 1000000
            except:
                date_value = hash(voice.get('voice_id', '')) % 1000000
                
            return (category_priority, date_value)
        
        custom_voices.sort(key=sort_key)
        logger.info(f"Found {len(custom_voices)} custom voices (sorted by deletion priority)")
        
        return custom_voices

    def delete_voice(self, voice_id: str) -> bool:
        """Delete a voice by ID"""
        url = f"{self.base_url}/voices/{voice_id}"

        try:
            response = requests.delete(url, headers=self.headers)
            response.raise_for_status()

            logger.info(f"Successfully deleted voice: {voice_id}")
            return True

        except requests.RequestException as e:
            logger.error(f"Failed to delete voice {voice_id}: {e}")
            # Log additional details for debugging
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Delete voice API error details: {error_detail}")
                except:
                    logger.error(f"Delete voice API response: {e.response.text}")
            return False

    def delete_oldest_voice(self) -> bool:
        """Delete the oldest custom voice (prioritizing cloned voices)"""
        custom_voices = self.get_custom_voices()
        if not custom_voices:
            logger.info("No custom voices found to delete")
            return True  # No voices to delete, consider it success

        # The list is already sorted with cloned voices first, then by date
        target_voice = custom_voices[0]
        voice_name = target_voice.get('name', 'Unknown')
        voice_category = target_voice.get('category', 'unknown')
        
        logger.info(f"Attempting to delete voice: {voice_name} ({target_voice['voice_id']}) - {voice_category}")
        
        success = self.delete_voice(target_voice['voice_id'])
        if success:
            logger.info(f"Successfully deleted voice: {voice_name}")
        else:
            logger.error(f"Failed to delete voice: {voice_name}")
            
        return success

    def create_voice_clone(self, audio_files: List[str], voice_name: str,
                          description: str = None) -> Optional[str]:
        """
        Create a voice clone from audio files
        Returns voice_id if successful, None if failed
        """
        url = f"{self.base_url}/voices/add"

        # Validate files exist
        valid_files = []
        for file_path in audio_files:
            if not Path(file_path).exists():
                logger.error(f"Audio file not found: {file_path}")
                continue
            valid_files.append(file_path)

        if not valid_files:
            logger.error("No valid audio files provided")
            return None

        # Prepare files for upload
        files = []
        total_size = 0

        try:
            for audio_file in valid_files:
                file_size = Path(audio_file).stat().st_size
                total_size += file_size

                # Check file size
                if file_size > settings.max_file_size_mb * 1024 * 1024:
                    logger.error(f"File too large: {audio_file} ({file_size} bytes)")
                    continue

                content_type = 'audio/mpeg' if audio_file.endswith('.mp3') else 'audio/wav'

                with open(audio_file, 'rb') as f:
                    files.append(('files', (Path(audio_file).name, f.read(), content_type)))

            if not files:
                logger.error("No valid files after size validation")
                return None

            data = {
                'name': voice_name,
                'description': description or f'Voice clone created from {len(files)} audio files',
                'remove_background_noise': 'true'
            }

            logger.info(f"Uploading {len(files)} files ({total_size:,} bytes) for voice clone")

            response = requests.post(url, headers=self.headers, files=files, data=data)
            response.raise_for_status()

            result = response.json()
            voice_id = result['voice_id']

            logger.info(f"Successfully created voice clone: {voice_name} ({voice_id})")
            return voice_id

        except requests.RequestException as e:
            logger.error(f"Failed to create voice clone: {e}")
            # Log response details if available
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"ElevenLabs API error details: {error_detail}")
                    
                    # Check for specific error types and raise more informative exceptions
                    detail = error_detail.get('detail', {})
                    if isinstance(detail, dict):
                        status = detail.get('status')
                        message = detail.get('message', str(e))
                        
                        if status == 'voice_limit_reached':
                            raise Exception(f"Voice limit reached: {message}")
                        elif status == 'quota_exceeded':
                            raise Exception(f"API quota exceeded: {message}")
                        elif 'audio' in message.lower() or 'quality' in message.lower():
                            raise Exception(f"Audio quality issue: {message}")
                        else:
                            raise Exception(f"ElevenLabs API error ({status}): {message}")
                    
                except:
                    logger.error(f"ElevenLabs API response text: {e.response.text}")
                    logger.error(f"ElevenLabs API response status: {e.response.status_code}")
                    
                    # Try to extract error message from response text
                    if e.response.status_code == 400:
                        raise Exception(f"Voice creation failed (HTTP 400): {e.response.text[:200]}")
                    
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating voice clone: {e}")
            return None

    def generate_speech(self, voice_id: str, text: str, model: str = "eleven_multilingual_v2",
                       stability: float = 0.6, similarity_boost: float = 0.8) -> Optional[bytes]:
        """Generate speech audio from text using specified voice and settings"""
        url = f"{self.base_url}/text-to-speech/{voice_id}"

        # Handle eleven_v3 special requirements
        if model == "eleven_v3":
            # eleven_v3 only accepts discrete stability values: 0.0, 0.5, 1.0
            if stability < 0.25:
                stability = 0.0  # Creative
            elif stability < 0.75:
                stability = 0.5  # Natural
            else:
                stability = 1.0  # Robust
            
            # eleven_v3 may have different similarity_boost limits
            similarity_boost = min(1.0, max(0.0, similarity_boost))

        payload = {
            "text": text,
            "model_id": model,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()

            audio_data = response.content
            logger.info(f"Generated speech audio: {len(audio_data):,} bytes")
            return audio_data

        except requests.RequestException as e:
            logger.error(f"Failed to generate speech: {e}")
            # Log response details if available
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"ElevenLabs speech API error details: {error_detail}")
                except:
                    logger.error(f"ElevenLabs speech API response text: {e.response.text}")
                    logger.error(f"ElevenLabs speech API response status: {e.response.status_code}")
            return None

    def check_voice_limit(self) -> Tuple[int, int]:
        """
        Check current voice usage against limit
        Returns (current_count, max_limit)
        """
        custom_voices = self.get_custom_voices()
        current_count = len(custom_voices)

        # ElevenLabs limits: Free=3, Starter=10, Creator=30, Pro=160
        # We'll assume Starter plan (10) as default
        max_limit = 10

        logger.info(f"Voice usage: {current_count}/{max_limit}")
        return current_count, max_limit

    def ensure_voice_capacity(self) -> bool:
        """Always delete oldest voice before creating new one"""
        return self.delete_oldest_voice()
    
    def ensure_voice_capacity_aggressive(self, target_free_slots: int = 2) -> bool:
        """
        Ensure voice capacity by deleting enough voices to have free slots AFTER creating a new voice
        
        Args:
            target_free_slots: Number of free slots to ensure AFTER creating the new voice
            
        Returns:
            True if capacity is available, False if failed
        """
        try:
            custom_voices = self.get_custom_voices()
            current_count = len(custom_voices)
            
            # Get actual limit from subscription if possible, otherwise assume 10
            max_limit = 10  # Default for Starter plan
            
            logger.info(f"Current voice usage: {current_count}/{max_limit}")
            
            # Calculate how many to delete accounting for the new voice that will be created
            # We need: current_count + 1 (new voice) + target_free_slots <= max_limit
            # So: current_count + 1 + target_free_slots <= max_limit
            # Therefore: voices_to_delete = max(0, current_count + 1 + target_free_slots - max_limit)
            voices_to_delete = max(0, current_count + 1 + target_free_slots - max_limit)
            
            if voices_to_delete == 0:
                logger.info(f"Voice capacity is sufficient: {current_count}/{max_limit} (will be {current_count + 1} after creation)")
                return True
                
            logger.info(f"Need to delete {voices_to_delete} voices to free up capacity")
            
            # Delete oldest voices
            for i in range(voices_to_delete):
                if not self.delete_oldest_voice():
                    logger.error(f"Failed to delete voice {i+1}/{voices_to_delete}")
                    return False
                logger.info(f"Deleted voice {i+1}/{voices_to_delete}")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure voice capacity: {e}")
            return False
