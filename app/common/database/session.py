"""Async database session management with SQLModel and MySQL."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
from app.common.config import settings

# Create async engine for MySQL
# Using asyncmy driver: mysql+asyncmy://user:password@host:port/database
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.

    Usage in FastAPI endpoints:
        async def my_endpoint(session: AsyncSession = Depends(get_async_session)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database - create all tables."""
    from app.common.database.base import SQLModel

    # Import all models here to ensure they are registered with SQLModel
    from app.features.users.models import User  # noqa: F401
    from app.features.courses.models import Course, Category, SubCategory  # noqa: F401
    from app.features.modules.models import Module  # noqa: F401
    from app.features.lessons.models import Lesson  # noqa: F401
    from app.features.quiz.models import Quiz, Question  # noqa: F401

    from app.features.subscriptions.models import (
        Subscription,
        SubscriptionUsage,
    )  # noqa: F401
    from app.features.logs.models import Log  # noqa: F401

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
