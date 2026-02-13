"""Database configuration with Supabase client and SQLAlchemy engine setup."""
import logging
from typing import AsyncGenerator, Optional, Dict, Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)
from sqlalchemy.orm import declarative_base
from supabase import create_client, Client

from .config import get_settings

logger = logging.getLogger(__name__)

# SQLAlchemy declarative base for all models
Base = declarative_base()


class DatabaseManager:
    """Manage Supabase client and SQLAlchemy database connections."""
    
    def __init__(self):
        self._engine = None
        self._session_factory = None
        self._supabase_client: Optional[Client] = None

    def initialize(self) -> None:
        """Initialize Supabase client and SQLAlchemy database engine."""
        settings = get_settings()
        
        # Initialize Supabase client
        self._initialize_supabase_client(settings)
        
        
        
        logger.info(f"✓ Database connections initialized in {settings.environment.value} mode")

    def _initialize_supabase_client(self, settings) -> None:
        """Initialize Supabase Python client."""
        supabase_url = settings.supabase_url
        supabase_key = settings.supabase_key.get_secret_value() if settings.supabase_key else None
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured in environment variables.")
        
        try:
            self._supabase_client = create_client(supabase_url, supabase_key)
            logger.info(f"✓ Supabase client initialized: {supabase_url}")
        except Exception as e:
            logger.error(f"✗ Failed to initialize Supabase client: {str(e)}")
            raise


    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session."""
        if self._session_factory is None:
            self.initialize()
        
        async with self._session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {str(e)}")
                raise
            finally:
                await session.close()

    async def close(self) -> None:
        """Close database connection pool."""
        if self._engine:
            await self._engine.dispose()
            logger.info("✓ Database connection pool closed")

    async def test_connection(self) -> bool:
        """Test database connectivity using both Supabase client and SQLAlchemy."""
        # Test Supabase client connection
        supabase_ok = await self._test_supabase_connection()
                
        return supabase_ok 

    async def _test_supabase_connection(self) -> bool:
        """Test Supabase client connection."""
        try:
            if not self._supabase_client:
                logger.error("Supabase client not initialized")
                return False
            
            # Test connection by making a simple request to auth
            response = self._supabase_client.auth.get_user()
            # Even if user is None, this means the client can communicate with Supabase
            logger.info(f"Supabase client connection successful")
            return True
        except Exception as e:
            logger.error(f"Supabase client connection test failed: {type(e).__name__}: {str(e)}")
            return False

    @property
    def engine(self):
        """Get SQLAlchemy engine."""
        if self._engine is None:
            self.initialize()
        return self._engine

    @property
    def session_factory(self):
        """Get session factory."""
        if self._session_factory is None:
            self.initialize()
        return self._session_factory

    @property
    def supabase(self) -> Client:
        """Get Supabase client."""
        if self._supabase_client is None:
            self.initialize()
        return self._supabase_client

    # Supabase convenience methods
    async def query_table(self, table: str, select: str = "*", filters: Optional[Dict[str, Any]] = None) -> Dict:
        """Query a table using Supabase client."""
        try:
            query = self.supabase.table(table).select(select)
            
            if filters:
                for column, value in filters.items():
                    query = query.eq(column, value)
            
            response = query.execute()
            return {"data": response.data, "count": response.count, "error": None}
        except Exception as e:
            logger.error(f"Supabase query failed for table {table}: {str(e)}")
            return {"data": None, "count": 0, "error": str(e)}

    async def insert_record(self, table: str, data: Dict[str, Any]) -> Dict:
        """Insert a record using Supabase client."""
        try:
            response = self.supabase.table(table).insert(data).execute()
            return {"data": response.data, "error": None}
        except Exception as e:
            logger.error(f"Supabase insert failed for table {table}: {str(e)}")
            return {"data": None, "error": str(e)}

    async def update_record(self, table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> Dict:
        """Update records using Supabase client."""
        try:
            query = self.supabase.table(table).update(data)
            
            for column, value in filters.items():
                query = query.eq(column, value)
            
            response = query.execute()
            return {"data": response.data, "error": None}
        except Exception as e:
            logger.error(f"✗ Supabase update failed for table {table}: {str(e)}")
            return {"data": None, "error": str(e)}

    async def delete_record(self, table: str, filters: Dict[str, Any]) -> Dict:
        """Delete records using Supabase client."""
        try:
            query = self.supabase.table(table).delete()
            
            for column, value in filters.items():
                query = query.eq(column, value)
            
            response = query.execute()
            return {"data": response.data, "error": None}
        except Exception as e:
            logger.error(f"✗ Supabase delete failed for table {table}: {str(e)}")
            return {"data": None, "error": str(e)}


# Global database manager
db_manager = DatabaseManager()



async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection for database session."""
    async for session in db_manager.get_session():
        yield session
