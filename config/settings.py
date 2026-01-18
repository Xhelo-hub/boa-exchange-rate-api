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
from dotenv import load_dotenv

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent  # config/settings.py -> config/ -> project_root/

# Load .env file manually to avoid Windows path issues
def load_env_file():
    """Manually load .env file to avoid path issues with python-dotenv"""
    env_path = PROJECT_ROOT / "config" / ".env"
    if env_path.exists():
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
        except Exception as e:
            print(f"Warning: Could not load .env file: {e}")

load_env_file()


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    app_url: str = "http://localhost:8000"  # Base URL for OAuth callbacks and links
    
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
    
    # Security Settings
    secret_key: Optional[str] = None
    admin_api_key: Optional[str] = None
    
    # Database Settings
    database_url: str = f"sqlite:///{str(PROJECT_ROOT / 'data' / 'boa_exchange.db').replace(chr(92), '/')}"
    
    class Config:
        # Disable automatic env_file loading due to Windows path issues
        # Load manually using python-dotenv instead
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure SECRET_KEY is set in os.environ for encryption manager
        if self.secret_key and 'SECRET_KEY' not in os.environ:
            os.environ['SECRET_KEY'] = self.secret_key


# Global settings instance
settings = Settings()