"""
Local development runner
Initializes database and starts the FastAPI server
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.init_db import init_database
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Initialize database and start server"""
    try:
        # Initialize database
        print("=" * 60)
        print("🚀 Starting BoA Exchange Rate API - Local Development")
        print("=" * 60)
        
        print("\n📊 Step 1: Initializing database...")
        init_database()
        print("✅ Database ready!")
        
        print("\n🔐 Step 2: Loading security configuration...")
        try:
            from config.settings import settings
            
            if not settings.secret_key:
                print("⚠️  WARNING: SECRET_KEY not set in .env!")
                print("   Token encryption will not work.")
            else:
                print(f"✅ SECRET_KEY loaded: {settings.secret_key[:10]}...")
                
            if not settings.admin_api_key:
                print("⚠️  WARNING: ADMIN_API_KEY not set in .env!")
                print("   Protected endpoints will not work.")
            else:
                print(f"✅ ADMIN_API_KEY loaded: {settings.admin_api_key[:10]}...")
        except Exception as e:
            print(f"⚠️  Warning loading settings: {e}")
        
        print("\n🌐 Step 3: Starting FastAPI server...")
        print(f"   Host: {settings.api_host}:{settings.api_port}")
        print(f"   Environment: {'SANDBOX' if settings.qb_sandbox else 'PRODUCTION'}")
        print(f"   Docs: http://localhost:{settings.api_port}/docs")
        print(f"   Health: http://localhost:{settings.api_port}/health")
        print("\n" + "=" * 60)
        print("💡 To connect QuickBooks:")
        print(f"   Visit: http://localhost:{settings.api_port}/api/v1/oauth/connect")
        print("=" * 60)
        print("\n🔑 Protected Endpoints require X-API-Key header:")
        print(f"   X-API-Key: {settings.admin_api_key}")
        print("=" * 60 + "\n")
        
        # Import and run uvicorn
        import uvicorn
        uvicorn.run(
            "src.main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=True,  # Enable auto-reload for development
            log_level=settings.log_level.lower()
        )
        
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
