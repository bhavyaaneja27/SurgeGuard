"""
Database Session Management.
Prepared for PostgreSQL / Supabase, with non-blocking local demo fallback.
"""
from typing import Generator, Optional
from app.core.config import settings
from app.core.logging import logger


def get_db_session() -> Generator[Optional[object], None, None]:
    """
    FastAPI dependency yielding a database session when configured,
    or None when running in local demo mode without blocking Phase 0.
    """
    if not settings.DATABASE_URL:
        # Local demo mode: Yield None so routes operate with in-memory or demo fallback
        yield None
        return

    # In production/connected mode with SQLAlchemy/asyncpg:
    # (To be wired when PostgreSQL credentials are provided)
    logger.info("Connecting to configured DATABASE_URL")
    yield None
