from contextlib import asynccontextmanager
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

# Create async engine with proper pool settings for Celery workers
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    future=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_timeout=30,
)

# Create async session maker
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def dispose_engine():
    """Dispose of the engine's connection pool. Useful for worker process initialization."""
    try:
        engine.sync_engine.dispose()
        logger.info("Database engine disposed successfully")
    except Exception as e:
        logger.error(f"Error disposing database engine: {e}")


@asynccontextmanager
async def task_db_session():
    """
    Fresh engine + session for Celery tasks.

    Each Celery task calls asyncio.run(), which creates a new event loop.
    Re-using the module-level pooled engine across loops causes:
      RuntimeError: Task got Future attached to a different loop
    NullPool disables connection reuse so every call gets a clean connection
    bound to the current loop.
    """
    task_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    task_session_maker = async_sessionmaker(task_engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with task_session_maker() as session:
            yield session
    finally:
        await task_engine.dispose()


async def get_db() -> AsyncSession:
    """Dependency for getting async database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Made with Bob
