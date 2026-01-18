"""
FastAPI application entry point for Bank of Albania Exchange Rate API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uvicorn
from pathlib import Path

from .api.routes import router
from .api.company_routes import router as company_router
from .api.oauth_routes import router as oauth_router
from .api.admin_routes import router as admin_router
from .api.registration_routes import router as registration_router
from .api.rates_routes import router as rates_router
from .utils.logger import get_logger
from .utils.scheduler import start_scheduler, stop_scheduler
from config.settings import settings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Bank of Albania Exchange Rate API")
    # start_scheduler()  # Temporarily disabled for testing
    yield
    # Shutdown
    logger.info("Shutting down Bank of Albania Exchange Rate API")
    # stop_scheduler()  # Temporarily disabled for testing


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

# Include API routes FIRST (before static files)
app.include_router(router, prefix="/api/v1")
app.include_router(company_router)
app.include_router(oauth_router)
app.include_router(admin_router)
app.include_router(registration_router)
app.include_router(rates_router)

# Mount static files LAST (to avoid interfering with API routes)
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Bank of Albania Exchange Rate API",
        "version": "0.1.0",
        "docs": "/docs",
        "admin": "/admin",
        "rates": "/rates",
        "register": "/register",
        "health": "/health"
    }


@app.get("/admin")
async def admin_dashboard():
    """Admin dashboard"""
    admin_html = Path(__file__).parent.parent / "static" / "admin.html"
    if admin_html.exists():
        return FileResponse(admin_html)
    else:
        raise HTTPException(status_code=404, detail="Admin dashboard not found")


@app.get("/register")
async def company_registration():
    """Public company registration page"""
    register_html = Path(__file__).parent.parent / "static" / "register.html"
    if register_html.exists():
        return FileResponse(register_html)
    else:
        raise HTTPException(status_code=404, detail="Registration page not found")


@app.get("/rates")
async def exchange_rates():
    """Public exchange rates page"""
    rates_html = Path(__file__).parent.parent / "static" / "rates.html"
    if rates_html.exists():
        return FileResponse(rates_html)
    else:
        raise HTTPException(status_code=404, detail="Rates page not found")


@app.get("/api/v1/callback")
async def oauth_callback_redirect(code: str, realmId: str, state: str = None):
    """Redirect QuickBooks OAuth callback to the proper handler"""
    from fastapi.responses import RedirectResponse
    redirect_url = f"/api/v1/oauth/callback?code={code}&realmId={realmId}"
    if state:
        redirect_url += f"&state={state}"
    return RedirectResponse(url=redirect_url, status_code=307)


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