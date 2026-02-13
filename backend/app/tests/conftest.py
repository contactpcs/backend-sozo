"""Test fixtures and configuration."""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.database import Base


@pytest.fixture
async def test_db():
    """Create test database."""
    # Use SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def test_settings():
    """Test settings."""
    from app.core.config import Settings
    return Settings(
        environment="dev",
        debug=True,
        jwt__secret_key="test-secret-key"
    )
