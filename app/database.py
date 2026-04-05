"""
TG PRO QUANTUM - PostgreSQL Database Connection (async SQLAlchemy)
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.config import settings

# SQLite (used in tests) doesn't support pool_size / max_overflow.
# Normalize plain sqlite:// → sqlite+aiosqlite:// so the async driver is used.
_db_url: str = settings.DATABASE_URL
if _db_url.startswith("sqlite://") and not _db_url.startswith("sqlite+"):
    _db_url = _db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

_is_sqlite = _db_url.startswith("sqlite")

_engine_kwargs: dict = {"echo": settings.DEBUG}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    _engine_kwargs["poolclass"] = StaticPool
else:
    _engine_kwargs["pool_pre_ping"] = True
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_async_engine(_db_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency – yields an async DB session."""
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
    """Create all tables on startup (use Alembic for migrations in production)."""
    from app.models import database as _models  # noqa: F401 – ensure models are loaded
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
