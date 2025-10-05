"""
Application settings and configuration
"""

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
    
from typing import Optional
import os
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    
    # Bank of Albania Settings
    boa_base_url: str = "https://www.bankofalbania.org"
    boa_timeout: int = 30
    
    # QuickBooks Online Settings
    qb_client_id: Optional[str] = None
    qb_client_secret: Optional[str] = None
    qb_access_token: Optional[str] = None
    qb_refresh_token: Optional[str] = None
    qb_company_id: Optional[str] = None
    qb_sandbox: bool = True
    qb_base_url: str = "https://sandbox-quickbooks.api.intuit.com"
    qb_redirect_uri: Optional[str] = "http://localhost:8000/callback"
    
    # Scheduler Settings
    schedule_time: str = "09:00"  # Daily update time (24h format)
    
    class Config:
        env_file = PROJECT_ROOT / "config" / ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()