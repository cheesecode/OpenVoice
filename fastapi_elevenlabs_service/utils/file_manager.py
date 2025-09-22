"""
File management utilities for audio files and output handling
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import logging
import tempfile
import uuid
from datetime import datetime, timedelta

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FileManager:
    """Professional file management for voice cloning service"""

    def __init__(self):
        self.output_dir = Path(settings.output_directory)
        self.temp_dir = Path(tempfile.gettempdir()) / "voice_cloning_temp"
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure required directories exist"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized directories: output={self.output_dir}, temp={self.temp_dir}")

    def validate_audio_files(self, file_paths: List[str]) -> Tuple[List[str], List[str]]:
        """
        Validate audio files for cloning

        Args:
            file_paths: List of file paths to validate

        Returns:
            Tuple of (valid_files, errors)
        """
        valid_files = []
        errors = []

        for file_path in file_paths:
            file_path = Path(file_path)

            # Check if file exists
            if not file_path.exists():
                errors.append(f"File not found: {file_path}")
                continue

            # Check file extension
            if file_path.suffix.lower() not in settings.allowed_extensions:
                errors.append(f"Invalid file format: {file_path.suffix}. Allowed: {settings.allowed_extensions}")
                continue

            # Check file size
            file_size = file_path.stat().st_size
            max_size = settings.max_file_size_mb * 1024 * 1024

            if file_size > max_size:
                errors.append(f"File too large: {file_path} ({file_size:,} bytes > {max_size:,} bytes)")
                continue

            if file_size < 1024:  # Less than 1KB
                errors.append(f"File too small: {file_path} ({file_size} bytes)")
                continue

            valid_files.append(str(file_path))

        logger.info(f"Validated {len(file_paths)} files: {len(valid_files)} valid, {len(errors)} errors")
        return valid_files, errors

    def save_uploaded_file(self, file_content: bytes, original_filename: str, job_id: str) -> Optional[str]:
        """
        Save uploaded file to temporary directory

        Args:
            file_content: File content bytes
            original_filename: Original filename
            job_id: Job identifier for organization

        Returns:
            Path to saved file or None if failed
        """
        try:
            # Create job-specific temp directory
            job_temp_dir = self.temp_dir / job_id
            job_temp_dir.mkdir(exist_ok=True)

            # Generate safe filename
            file_extension = Path(original_filename).suffix.lower()
            safe_filename = f"{uuid.uuid4().hex}{file_extension}"
            file_path = job_temp_dir / safe_filename

            # Save file
            with open(file_path, 'wb') as f:
                f.write(file_content)

            logger.info(f"Saved uploaded file: {file_path} ({len(file_content):,} bytes)")
            return str(file_path)

        except Exception as e:
            logger.error(f"Failed to save uploaded file {original_filename}: {e}")
            return None

    def save_generated_audio(self, audio_data: bytes, job_id: str, voice_name: str) -> Optional[str]:
        """
        Save generated audio to output directory

        Args:
            audio_data: Audio content bytes
            job_id: Job identifier
            voice_name: Voice name for filename

        Returns:
            Path to saved file or None if failed
        """
        try:
            # Generate output filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            safe_voice_name = self._sanitize_filename(voice_name)
            filename = f"{job_id}_{safe_voice_name}_{timestamp}.mp3"
            output_path = self.output_dir / filename

            # Save audio file
            with open(output_path, 'wb') as f:
                f.write(audio_data)

            logger.info(f"Saved generated audio: {output_path} ({len(audio_data):,} bytes)")
            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to save generated audio for job {job_id}: {e}")
            return None

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file system usage"""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        sanitized = ''.join(c if c not in invalid_chars else '_' for c in filename)

        # Limit length and remove leading/trailing dots/spaces
        sanitized = sanitized.strip(' .')[:50]

        # Ensure we have a valid filename
        if not sanitized:
            sanitized = "voice_clone"

        return sanitized

    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed file information

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file information or None if file doesn't exist
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return None

            stat = file_path.stat()
            info = {
                "path": str(file_path),
                "name": file_path.name,
                "extension": file_path.suffix.lower(),
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_valid_audio": file_path.suffix.lower() in settings.allowed_extensions
            }

            return info

        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {e}")
            return None

    def cleanup_temp_files(self, job_id: str) -> bool:
        """
        Clean up temporary files for a job

        Args:
            job_id: Job identifier

        Returns:
            Success status
        """
        try:
            job_temp_dir = self.temp_dir / job_id
            if job_temp_dir.exists():
                shutil.rmtree(job_temp_dir)
                logger.info(f"Cleaned up temp files for job: {job_id}")
                return True

            return True  # Nothing to clean up

        except Exception as e:
            logger.error(f"Failed to cleanup temp files for job {job_id}: {e}")
            return False

    def cleanup_old_files(self, max_age_hours: int = 24) -> Dict[str, int]:
        """
        Clean up old files from temp and output directories

        Args:
            max_age_hours: Maximum file age in hours

        Returns:
            Dictionary with cleanup statistics
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        stats = {"temp_files_deleted": 0, "output_files_deleted": 0, "errors": 0}

        # Clean temp directory
        try:
            for item in self.temp_dir.iterdir():
                if item.is_dir():
                    try:
                        # Check if directory is old
                        if datetime.fromtimestamp(item.stat().st_mtime) < cutoff_time:
                            shutil.rmtree(item)
                            stats["temp_files_deleted"] += 1
                    except Exception as e:
                        logger.error(f"Failed to delete temp directory {item}: {e}")
                        stats["errors"] += 1

        except Exception as e:
            logger.error(f"Error cleaning temp directory: {e}")
            stats["errors"] += 1

        # Clean output directory (optional - be careful with user data)
        try:
            for item in self.output_dir.iterdir():
                if item.is_file():
                    try:
                        # Only delete very old files (be conservative)
                        file_age_hours = max_age_hours * 24  # Much older for output files
                        old_cutoff = datetime.utcnow() - timedelta(hours=file_age_hours)

                        if datetime.fromtimestamp(item.stat().st_mtime) < old_cutoff:
                            item.unlink()
                            stats["output_files_deleted"] += 1

                    except Exception as e:
                        logger.error(f"Failed to delete output file {item}: {e}")
                        stats["errors"] += 1

        except Exception as e:
            logger.error(f"Error cleaning output directory: {e}")
            stats["errors"] += 1

        logger.info(f"File cleanup completed: {stats}")
        return stats

    def get_directory_stats(self) -> Dict[str, Any]:
        """Get statistics about directories and files"""
        stats = {
            "output_directory": str(self.output_dir),
            "temp_directory": str(self.temp_dir),
            "output_files": 0,
            "output_size_mb": 0,
            "temp_directories": 0,
            "temp_size_mb": 0
        }

        try:
            # Output directory stats
            if self.output_dir.exists():
                output_files = list(self.output_dir.glob("*"))
                stats["output_files"] = len([f for f in output_files if f.is_file()])
                stats["output_size_mb"] = round(
                    sum(f.stat().st_size for f in output_files if f.is_file()) / (1024 * 1024), 2
                )

            # Temp directory stats
            if self.temp_dir.exists():
                temp_dirs = list(self.temp_dir.glob("*"))
                stats["temp_directories"] = len([d for d in temp_dirs if d.is_dir()])

                temp_size = 0
                for temp_dir in temp_dirs:
                    if temp_dir.is_dir():
                        for file in temp_dir.rglob("*"):
                            if file.is_file():
                                temp_size += file.stat().st_size

                stats["temp_size_mb"] = round(temp_size / (1024 * 1024), 2)

        except Exception as e:
            logger.error(f"Error getting directory stats: {e}")

        return stats

    def is_file_accessible(self, file_path: str) -> bool:
        """Check if file is accessible for reading"""
        try:
            file_path = Path(file_path)
            return file_path.exists() and file_path.is_file() and os.access(file_path, os.R_OK)
        except Exception:
            return False


# Global file manager instance
file_manager = FileManager()


def get_file_manager() -> FileManager:
    """Get global file manager instance"""
    return file_manager