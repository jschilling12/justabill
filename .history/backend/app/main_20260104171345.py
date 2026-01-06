from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from app.config import settings
from app.database import get_db, engine
from app.models import Base
from app import routers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting Just A Bill API...")
    logger.info(f"Database: {settings.DATABASE_URL}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    
    # Create tables (in production, use Alembic migrations)
    # Base.metadata.create_all(bind=engine)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Just A Bill API...")


# Create FastAPI app
app = FastAPI(
    title="Just A Bill API",
    description="API for the Bill Vote Breakdown application",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "status_code": 500}
    )


# Include routers
from app.routers import health, bills, ingestion, votes, auth

app.include_router(health.router, tags=["health"])
app.include_router(bills.router, prefix="/bills", tags=["bills"])
app.include_router(ingestion.router, prefix="/ingest", tags=["ingestion"])
app.include_router(votes.router, prefix="/votes", tags=["votes"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Just A Bill API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True
    )
