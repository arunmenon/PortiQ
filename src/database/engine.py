from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    max_overflow=5,
    echo=settings.environment == "development",
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Synchronous engine for Alembic migrations and Celery tasks
sync_engine = create_engine(
    settings.database_url_sync,
    pool_size=5,
    pool_pre_ping=True,
)
