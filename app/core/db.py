"""Database engine and session helpers."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import settings


engine: AsyncEngine = create_async_engine(
    settings.sqlalchemy_url,
    echo=settings.echo_sql,
    pool_pre_ping=True,
)

AsyncSessionMaker = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async SQLAlchemy session."""

    async with AsyncSessionMaker() as session:
        yield session

