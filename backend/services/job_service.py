"""Job service for async multi-agent processing using Redis."""
import json
import uuid
import asyncio
import structlog
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis
from backend.config import settings
from backend.models.schemas import (
    MultiAgentRequest, MultiAgentResponse, 
    JobStatusResponse, JobResultResponse
)

logger = structlog.get_logger()

# Redis key prefixes
JOB_PREFIX = "job:"
JOB_STATUS_PREFIX = "job:status:"
JOB_RESULT_PREFIX = "job:result:"
JOB_EXPIRY_SECONDS = 3600  # 1 hour


class JobService:
    """Service for managing async multi-agent processing jobs."""
    
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
    
    async def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get or create Redis client."""
        if self._redis_client is None:
            try:
                redis_url = settings.redis_url
                self._redis_client = await redis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self._redis_client.ping()
                logger.info("job_service_redis_connected", url=redis_url)
            except Exception as e:
                logger.error("job_service_redis_connection_failed", error=str(e))
                raise
        return self._redis_client
    
    async def create_job(
        self, 
        request: MultiAgentRequest,
        user_id: str
    ) -> str:
        """Create a new job and return job ID."""
        job_id = str(uuid.uuid4())
        redis_client = await self._get_redis_client()
        
        job_data = {
            "job_id": job_id,
            "user_id": user_id,
            "request": request.model_dump_json(),
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "progress": 0.0,
            "message": "Job queued for processing"
        }
        
        # Store job data
        await redis_client.setex(
            f"{JOB_PREFIX}{job_id}",
            JOB_EXPIRY_SECONDS,
            json.dumps(job_data)
        )
        
        # Store status separately for quick access
        await redis_client.setex(
            f"{JOB_STATUS_PREFIX}{job_id}",
            JOB_EXPIRY_SECONDS,
            json.dumps({
                "status": "pending",
                "progress": 0.0,
                "message": "Job queued for processing",
                "created_at": job_data["created_at"],
                "updated_at": job_data["updated_at"]
            })
        )
        
        logger.info("job_created", job_id=job_id, user_id=user_id)
        return job_id
    
    async def get_job_status(self, job_id: str) -> Optional[JobStatusResponse]:
        """Get job status."""
        redis_client = await self._get_redis_client()
        
        status_data = await redis_client.get(f"{JOB_STATUS_PREFIX}{job_id}")
        if not status_data:
            return None
        
        status_dict = json.loads(status_data)
        
        # Calculate estimated remaining time if processing
        estimated_remaining = None
        if status_dict["status"] == "processing":
            # Estimate based on progress (rough estimate: 5 minutes total)
            progress = status_dict.get("progress", 0.0)
            if progress > 0:
                elapsed = (datetime.utcnow() - datetime.fromisoformat(status_dict["created_at"])).total_seconds()
                if progress < 1.0:
                    estimated_remaining = int((elapsed / progress) * (1.0 - progress))
        
        return JobStatusResponse(
            job_id=job_id,
            status=status_dict["status"],
            progress=status_dict.get("progress"),
            message=status_dict.get("message"),
            created_at=datetime.fromisoformat(status_dict["created_at"]),
            updated_at=datetime.fromisoformat(status_dict["updated_at"]),
            estimated_remaining_seconds=estimated_remaining
        )
    
    async def get_job_result(self, job_id: str) -> Optional[JobResultResponse]:
        """Get job result."""
        redis_client = await self._get_redis_client()
        
        result_data = await redis_client.get(f"{JOB_RESULT_PREFIX}{job_id}")
        if not result_data:
            # Check if job exists but not completed
            status = await self.get_job_status(job_id)
            if status and status.status in ["pending", "processing"]:
                return None
            return None
        
        result_dict = json.loads(result_data)
        
        result = None
        if result_dict.get("result"):
            result = MultiAgentResponse(**result_dict["result"])
        
        return JobResultResponse(
            job_id=job_id,
            status=result_dict["status"],
            result=result,
            error=result_dict.get("error"),
            created_at=datetime.fromisoformat(result_dict["created_at"]),
            completed_at=datetime.fromisoformat(result_dict["completed_at"]) if result_dict.get("completed_at") else None
        )
    
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: Optional[float] = None,
        message: Optional[str] = None
    ):
        """Update job status."""
        redis_client = await self._get_redis_client()
        
        # Get current job data
        job_data_str = await redis_client.get(f"{JOB_PREFIX}{job_id}")
        if not job_data_str:
            logger.warning("job_not_found_for_status_update", job_id=job_id)
            return
        
        job_data = json.loads(job_data_str)
        job_data["status"] = status
        job_data["updated_at"] = datetime.utcnow().isoformat()
        if progress is not None:
            job_data["progress"] = progress
        if message:
            job_data["message"] = message
        
        # Update job data
        ttl = await redis_client.ttl(f"{JOB_PREFIX}{job_id}")
        await redis_client.setex(
            f"{JOB_PREFIX}{job_id}",
            ttl if ttl > 0 else JOB_EXPIRY_SECONDS,
            json.dumps(job_data)
        )
        
        # Update status
        status_data = {
            "status": status,
            "progress": progress if progress is not None else job_data.get("progress", 0.0),
            "message": message or job_data.get("message", ""),
            "created_at": job_data["created_at"],
            "updated_at": job_data["updated_at"]
        }
        await redis_client.setex(
            f"{JOB_STATUS_PREFIX}{job_id}",
            ttl if ttl > 0 else JOB_EXPIRY_SECONDS,
            json.dumps(status_data)
        )
        
        logger.info("job_status_updated", job_id=job_id, status=status, progress=progress)
    
    async def save_job_result(
        self,
        job_id: str,
        result: Optional[MultiAgentResponse] = None,
        error: Optional[str] = None
    ):
        """Save job result."""
        redis_client = await self._get_redis_client()
        
        # Get job data for created_at
        job_data_str = await redis_client.get(f"{JOB_PREFIX}{job_id}")
        created_at = datetime.utcnow().isoformat()
        if job_data_str:
            job_data = json.loads(job_data_str)
            created_at = job_data.get("created_at", created_at)
        
        status = "completed" if result else "failed"
        
        result_data = {
            "job_id": job_id,
            "status": status,
            "result": result.model_dump() if result else None,
            "error": error,
            "created_at": created_at,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        ttl = await redis_client.ttl(f"{JOB_PREFIX}{job_id}")
        await redis_client.setex(
            f"{JOB_RESULT_PREFIX}{job_id}",
            ttl if ttl > 0 else JOB_EXPIRY_SECONDS,
            json.dumps(result_data)
        )
        
        # Update status to final state
        await self.update_job_status(
            job_id,
            status,
            progress=1.0 if result else None,
            message="Job completed" if result else f"Job failed: {error}"
        )
        
        logger.info("job_result_saved", job_id=job_id, status=status)
    
    async def process_job_background(
        self,
        job_id: str,
        request: MultiAgentRequest,
        orchestrator: Any
    ):
        """Process job in background (to be called from background task)."""
        try:
            await self.update_job_status(
                job_id,
                "processing",
                progress=0.1,
                message="Starting multi-agent processing..."
            )
            
            # Process the request
            response = await orchestrator.process_multi_agent_request(
                user_id=request.user_id,
                request=request
            )
            
            await self.update_job_status(
                job_id,
                "processing",
                progress=0.9,
                message="Finalizing response..."
            )
            
            # Save result
            await self.save_job_result(job_id, result=response)
            
        except Exception as e:
            logger.error("job_processing_failed", job_id=job_id, error=str(e))
            await self.save_job_result(job_id, error=str(e))


# Global job service instance
job_service = JobService()

