from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import redis

from app.database import get_db
from app.config import settings
from app.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    
    # Check database
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check Redis
    redis_status = "ok"
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
    except Exception as e:
        redis_status = f"error: {str(e)}"
    
    return HealthResponse(
        status="healthy" if db_status == "ok" and redis_status == "ok" else "degraded",
        timestamp=datetime.utcnow(),
        database=db_status,
        redis=redis_status
    )


@router.get("/health/llm")
async def check_llm_connection():
    """Check LLM configuration and test connection"""
    from app.llm_client import get_llm_client
    
    result = {
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "api_key_set": bool(settings.LLM_API_KEY),
        "api_key_preview": settings.LLM_API_KEY[:10] + "..." if settings.LLM_API_KEY else None,
        "base_url": settings.LLM_BASE_URL or "(default)",
        "connection_test": None,
        "error": None
    }
    
    # Test the actual LLM connection with a simple prompt
    try:
        client = get_llm_client()
        summary = await client.generate_summary(
            section_text="This section establishes that the short title of this Act is the 'Test Act of 2026'.",
            section_key="SEC. 1",
            heading="Short title"
        )
        result["connection_test"] = "SUCCESS"
        result["test_response"] = {
            "bullets": summary.plain_summary_bullets[:2] if summary.plain_summary_bullets else [],
            "evidence_count": len(summary.evidence_quotes) if summary.evidence_quotes else 0
        }
    except Exception as e:
        result["connection_test"] = "FAILED"
        result["error"] = str(e)
    
    return result


@router.get("/health/celery")
async def check_celery_status():
    """Check Celery worker status and pending tasks"""
    from app.celery_app import celery_app
    
    result = {
        "broker_url": settings.CELERY_BROKER_URL,
        "workers": None,
        "pending_tasks": None,
        "error": None
    }
    
    try:
        # Check for active workers
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            result["workers"] = list(active_workers.keys())
            # Count pending tasks per worker
            reserved = inspect.reserved() or {}
            result["pending_tasks"] = sum(len(tasks) for tasks in reserved.values())
        else:
            result["workers"] = []
            result["error"] = "No active Celery workers found"
    except Exception as e:
        result["error"] = str(e)
    
    return result
