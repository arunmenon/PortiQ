from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.engine import async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
