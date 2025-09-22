"""
Async job queue manager for voice cloning tasks
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import logging
from enum import Enum
from dataclasses import dataclass, asdict
import threading
import time

from models.responses import JobStatus
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class QueueJob:
    """Job data structure for queue management"""
    job_id: str
    job_type: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    data: Dict[str, Any]
    progress: int = 0
    error_message: Optional[str] = None
    retry_count: int = 0
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for serialization"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['updated_at'] = self.updated_at.isoformat() if self.updated_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        data['status'] = self.status.value if isinstance(self.status, JobStatus) else self.status
        return data


class InMemoryQueue:
    """In-memory job queue implementation (fallback for Redis)"""

    def __init__(self):
        self.jobs: Dict[str, QueueJob] = {}
        self.pending_jobs: asyncio.Queue = asyncio.Queue()
        self.lock = asyncio.Lock()
        self.stats = {
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "active_jobs": 0
        }

    async def enqueue(self, job: QueueJob):
        """Add job to queue"""
        async with self.lock:
            self.jobs[job.job_id] = job
            await self.pending_jobs.put(job.job_id)
            self.stats["total_jobs"] += 1
            logger.info(f"Enqueued job: {job.job_id}")

    async def dequeue(self) -> Optional[QueueJob]:
        """Get next job from queue"""
        try:
            job_id = await asyncio.wait_for(self.pending_jobs.get(), timeout=1.0)
            async with self.lock:
                job = self.jobs.get(job_id)
                if job and job.status == JobStatus.PENDING:
                    job.status = JobStatus.PROCESSING
                    job.updated_at = datetime.utcnow()
                    self.stats["active_jobs"] += 1
                    return job
        except asyncio.TimeoutError:
            return None
        return None

    async def update_job(self, job_id: str, **updates):
        """Update job status and data"""
        async with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]

                # Update fields
                for key, value in updates.items():
                    if hasattr(job, key):
                        setattr(job, key, value)

                job.updated_at = datetime.utcnow()

                # Update stats
                if 'status' in updates:
                    new_status = updates['status']
                    if new_status == JobStatus.COMPLETED:
                        self.stats["completed_jobs"] += 1
                        self.stats["active_jobs"] = max(0, self.stats["active_jobs"] - 1)
                        job.completed_at = datetime.utcnow()
                    elif new_status == JobStatus.FAILED:
                        self.stats["failed_jobs"] += 1
                        self.stats["active_jobs"] = max(0, self.stats["active_jobs"] - 1)

    async def get_job(self, job_id: str) -> Optional[QueueJob]:
        """Get job by ID"""
        return self.jobs.get(job_id)

    async def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return self.stats.copy()


class QueueManager:
    """Professional queue manager with Redis fallback to in-memory"""

    def __init__(self):
        self.queue = InMemoryQueue()  # Fallback to in-memory queue
        self.workers: List[asyncio.Task] = []
        self.running = False
        self.job_processors: Dict[str, Callable] = {}

    def register_processor(self, job_type: str, processor_func: Callable):
        """Register a job processor function for a specific job type"""
        self.job_processors[job_type] = processor_func
        logger.info(f"Registered processor for job type: {job_type}")

    async def submit_job(self, job_type: str, data: Dict[str, Any]) -> str:
        """
        Submit a new job to the queue

        Args:
            job_type: Type of job to process
            data: Job data dictionary

        Returns:
            job_id: Unique job identifier
        """
        job_id = f"vcj_{uuid.uuid4().hex[:12]}"

        job = QueueJob(
            job_id=job_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            data=data
        )

        await self.queue.enqueue(job)
        logger.info(f"Submitted job {job_id} of type {job_type}")
        return job_id

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status and details"""
        job = await self.queue.get_job(job_id)
        if job:
            return job.to_dict()
        return None

    async def update_job_progress(self, job_id: str, progress: int, message: str = None):
        """Update job progress"""
        updates = {"progress": progress}
        if message:
            updates["data"] = {**(await self.queue.get_job(job_id)).data, "message": message}

        await self.queue.update_job(job_id, **updates)

    async def complete_job(self, job_id: str, result: Dict[str, Any]):
        """Mark job as completed with result"""
        await self.queue.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            result=result
        )
        logger.info(f"Job completed: {job_id}")

    async def fail_job(self, job_id: str, error_message: str):
        """Mark job as failed with error message"""
        await self.queue.update_job(
            job_id,
            status=JobStatus.FAILED,
            error_message=error_message
        )
        logger.error(f"Job failed: {job_id} - {error_message}")

    async def start_workers(self, num_workers: int = None):
        """Start background worker processes"""
        if self.running:
            logger.warning("Workers already running")
            return

        num_workers = num_workers or settings.max_concurrent_jobs
        self.running = True

        for i in range(num_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)

        logger.info(f"Started {num_workers} queue workers")

    async def stop_workers(self):
        """Stop all background workers"""
        if not self.running:
            return

        self.running = False

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)

        self.workers.clear()
        logger.info("Stopped all queue workers")

    async def _worker(self, worker_name: str):
        """Background worker process"""
        logger.info(f"Worker {worker_name} started")

        while self.running:
            try:
                # Get next job
                job = await self.queue.dequeue()
                if not job:
                    continue

                logger.info(f"Worker {worker_name} processing job: {job.job_id}")

                # Process job
                await self._process_job(job)

            except asyncio.CancelledError:
                logger.info(f"Worker {worker_name} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")

        logger.info(f"Worker {worker_name} stopped")

    async def _process_job(self, job: QueueJob):
        """Process a single job"""
        try:
            # Update progress
            await self.update_job_progress(job.job_id, 10, "Starting job processing")

            # Get processor function
            processor = self.job_processors.get(job.job_type)
            if not processor:
                raise ValueError(f"No processor registered for job type: {job.job_type}")

            # Call processor function
            result = await processor(job)

            # Complete job
            await self.complete_job(job.job_id, result)

        except Exception as e:
            error_message = str(e)
            logger.error(f"Job processing failed: {job.job_id} - {error_message}")
            await self.fail_job(job.job_id, error_message)

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        stats = await self.queue.get_stats()
        stats.update({
            "workers_running": len([w for w in self.workers if not w.done()]),
            "queue_size": self.queue.pending_jobs.qsize() if hasattr(self.queue.pending_jobs, 'qsize') else 0
        })
        return stats

    async def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed/failed jobs

        Args:
            max_age_hours: Maximum job age in hours

        Returns:
            Number of jobs cleaned up
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleaned_count = 0

        jobs_to_remove = []
        for job_id, job in self.queue.jobs.items():
            if (job.status in [JobStatus.COMPLETED, JobStatus.FAILED] and
                job.updated_at < cutoff_time):
                jobs_to_remove.append(job_id)

        for job_id in jobs_to_remove:
            del self.queue.jobs[job_id]
            cleaned_count += 1

        logger.info(f"Cleaned up {cleaned_count} old jobs")
        return cleaned_count


# Global queue manager instance
queue_manager = QueueManager()


def get_queue_manager() -> QueueManager:
    """Get global queue manager instance"""
    return queue_manager