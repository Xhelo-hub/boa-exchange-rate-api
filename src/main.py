"""
FastAPI application entry point for Bank of Albania Exchange Rate API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from .api.routes import router
from .utils.logger import get_logger
from .utils.scheduler import start_scheduler, stop_scheduler
from .config.settings import settings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Bank of Albania Exchange Rate API")
    start_scheduler()
    yield
    # Shutdown
    logger.info("Shutting down Bank of Albania Exchange Rate API")
    stop_scheduler()


app = FastAPI(
    title="Bank of Albania Exchange Rate API",
    description="API to scrape exchange rates from Bank of Albania and sync with QuickBooks Online",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Bank of Albania Exchange Rate API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "boa-exchange-rate-api",
        "version": "0.1.0"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )