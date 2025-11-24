"""
Database engine and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
import os
from pathlib import Path

from .models import Base
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """
    Manages database connections and sessions
    
    Supports multiple database backends:
    - SQLite (default, for development and small deployments)
    - PostgreSQL (recommended for production)
    - MySQL/MariaDB (alternative for production)
    """
    
    def __init__(self, database_url: str = None):
        """
        Initialize database manager
        
        Args:
            database_url: SQLAlchemy database URL
                         If None, uses SQLite in project data directory
        """
        if database_url is None:
            # Default: SQLite database in project's data directory
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / 'data'
            data_dir.mkdir(exist_ok=True)
            
            db_path = data_dir / 'boa_exchange_rates.db'
            database_url = f'sqlite:///{db_path}'
            logger.info(f"Using SQLite database at: {db_path}")
        
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Create database engine and session factory"""
        try:
            # Create engine
            if self.database_url.startswith('sqlite'):
                # SQLite-specific configuration
                self.engine = create_engine(
                    self.database_url,
                    connect_args={'check_same_thread': False},  # Allow multi-threading
                    poolclass=NullPool  # SQLite doesn't need connection pooling
                )
            else:
                # PostgreSQL/MySQL configuration
                self.engine = create_engine(
                    self.database_url,
                    pool_pre_ping=True,  # Verify connections before using
                    pool_size=5,
                    max_overflow=10
                )
            
            # Create session factory
            self.SessionLocal = scoped_session(
                sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=self.engine
                )
            )
            
            logger.info("Database engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {e}")
            raise
    
    def create_tables(self):
        """Create all tables if they don't exist"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all tables (use with caution!)"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions
        
        Usage:
            with db_manager.get_session() as session:
                # Use session here
                pass
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_db(self):
        """
        Generator for FastAPI dependency injection
        
        Usage in FastAPI:
            @app.get("/rates")
            def get_rates(db: Session = Depends(db_manager.get_db)):
                # Use db here
                pass
        """
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def close(self):
        """Close database connections"""
        if self.SessionLocal:
            self.SessionLocal.remove()
        if self.engine:
            self.engine.dispose()
        logger.info("Database connections closed")


# Global database manager instance
_db_manager = None


def get_db_manager(database_url: str = None) -> DatabaseManager:
    """
    Get or create the global database manager instance
    
    Args:
        database_url: Database connection string (optional)
    
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager(database_url)
        _db_manager.create_tables()
    
    return _db_manager


def init_database(database_url: str = None):
    """
    Initialize the database (call this on application startup)
    
    Args:
        database_url: Database connection string (optional)
    """
    db_manager = get_db_manager(database_url)
    logger.info("Database initialized and ready")
    return db_manager
