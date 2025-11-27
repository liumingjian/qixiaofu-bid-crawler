"""Database configuration and session management."""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

Base = declarative_base()


class Database:
    """Database connection manager."""
    
    def __init__(self, config: dict):
        """
        Initialize database connection.
        
        Args:
            config: Root configuration dict that may include:
                - database.url: Full SQLAlchemy URL (overrides other fields)
                - database.host/port/name/user/password: Connection pieces for PostgreSQL
                - database.echo: Enable SQL echo for debugging
        """
        self.config = config
        self._engine = None
        self._session_factory = None
    
    def get_engine(self):
        """Get or create SQLAlchemy engine."""
        if self._engine is None:
            db_config = self.config.get("database", {})
            
            # Support overriding via explicit URL or environment variables
            conn_str = os.environ.get("DB_URL") or db_config.get("url")
            if not conn_str:
                host = os.environ.get("DB_HOST", db_config.get("host", "localhost"))
                port = os.environ.get("DB_PORT", db_config.get("port", 5432))
                name = os.environ.get("DB_NAME", db_config.get("name", "qixiaofu_crawler"))
                user = os.environ.get("DB_USER", db_config.get("user", "postgres"))
                password = os.environ.get("DB_PASSWORD", db_config.get("password", ""))
                conn_str = f"postgresql://{user}:{password}@{host}:{port}/{name}"
            
            engine_kwargs = {
                "pool_pre_ping": True,
                "echo": bool(db_config.get("echo", False)),
            }
            
            if conn_str.startswith("sqlite"):
                engine_kwargs["poolclass"] = NullPool
                engine_kwargs["connect_args"] = {"check_same_thread": False}
            else:
                engine_kwargs["pool_size"] = int(db_config.get("pool_size", 5))
                engine_kwargs["max_overflow"] = int(db_config.get("max_overflow", 10))
            
            self._engine = create_engine(conn_str, **engine_kwargs)
        
        return self._engine
    
    def get_session_factory(self):
        """Get or create session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.get_engine(),
                autocommit=False,
                autoflush=False
            )
        return self._session_factory
    
    def get_session(self) -> Session:
        """Create a new database session."""
        factory = self.get_session_factory()
        return factory()
    
    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.get_engine())
    
    def drop_tables(self):
        """Drop all database tables (use with caution!)."""
        Base.metadata.drop_all(bind=self.get_engine())

    def test_connection(self) -> bool:
        """Test if the database connection is working."""
        try:
            engine = self.get_engine()
            # Log the connection string (mask password for security if possible, but for debug we need to know structure)
            # URL is in engine.url
            # print(f"DEBUG: Testing connection to {engine.url}") 
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            # We need to know why it failed
            import logging
            logging.getLogger("WebApp").error(f"Database connection test failed: {e}")
            return False

    def reload_config(self, config: dict):
        """Update configuration and reset engine."""
        self.config = config
        if self._engine:
            self._engine.dispose()
            self._engine = None
        if self._session_factory:
            self._session_factory = None
        # Verify new config
        try:
            return self.test_connection()
        except Exception as e:
            import logging
            logging.getLogger("WebApp").error(f"Reload config failed: {e}")
            return False


# Global database instance (initialized by app)
_db: Optional[Database] = None


def init_db(config: dict) -> Database:
    """Initialize the global database instance."""
    global _db
    _db = Database(config)
    return _db


def get_db() -> Database:
    """Get the global database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db
