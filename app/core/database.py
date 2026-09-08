from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

# Normalize DATABASE_URL for asyncpg driver (e.g. Neon or Heroku postgres:// URLs)
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Normalize asyncpg query parameters (convert sslmode -> ssl, strip channel_binding)
if "sslmode=" in db_url:
    db_url = db_url.replace("sslmode=require", "ssl=require").replace("sslmode=prefer", "ssl=prefer")
if "&channel_binding=" in db_url:
    import re
    db_url = re.sub(r"&channel_binding=[^&]*", "", db_url)
if "?channel_binding=" in db_url:
    import re
    db_url = re.sub(r"\?channel_binding=[^&]*&?", "?", db_url)

# Create async engine using asyncpg driver with tuned connection pool parameters
async_engine: AsyncEngine = create_async_engine(
    db_url,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG,
)

# Async session factory configured with expire_on_commit=False for async context behavior
async_session_maker = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an isolated async SQLAlchemy session per request.
    Automatically closes the session after request completion or exception.
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
