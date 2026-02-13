"""Alembic configuration for database migrations.

Supports async SQLAlchemy with PostgreSQL and other async-capable databases.
"""
import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# this is the Alembic Config object, which provides
# the values of the alembic.ini file, as well as
# programmatic functions to configure programmatic
# features of Alembic.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from app.core.database import Base
target_metadata = Base.metadata


def get_database_url() -> str:
    """Get database URL from environment or config."""
    return os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/sozo_dev")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.
    
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Run the actual migration."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine.
    
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    url = get_database_url()
    
    # Create async engine for migrations
    connectable = create_async_engine(
        url,
        echo=False,
    )

    async with connectable.begin() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
