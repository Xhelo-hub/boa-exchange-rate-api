"""
Database initialization script
Creates tables for multi-tenant architecture
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path

from .models import Base
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Get project root and ensure data directory exists
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Create SQLite database in data directory
DATABASE_URL = f"sqlite:///{DATA_DIR / 'boa_exchange.db'}"


def init_database():
    """Initialize database with all tables"""
    try:
        logger.info(f"Initializing database at: {DATABASE_URL}")
        
        # Create engine
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False}  # Needed for SQLite
        )
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database initialized successfully")
        logger.info("Tables created: companies, exchange_rates, scraping_logs, quickbooks_syncs")
        
        return engine
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def get_session():
    """Get database session"""
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


if __name__ == "__main__":
    # Run directly to initialize database
    init_database()
    print("✅ Database initialized successfully!")
