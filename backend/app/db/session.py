from contextlib import contextmanager
from typing import Generator
from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("coverwise.db")

SUPPORTED_SCHEMES = ("postgresql", "postgresql+psycopg2", "postgresql+psycopg", "sqlite", "postgres")


def validate_database_url(url: str) -> str:
    """Validate DATABASE_URL configuration and ensure supported dialect scheme."""
    if not url or not url.strip():
        raise ValueError(
            "DATABASE_URL configuration is missing or empty. Please specify a valid database connection string."
        )

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if not any(scheme == s or scheme.startswith(s) for s in SUPPORTED_SCHEMES):
        raise ValueError(
            f"Unsupported database scheme '{scheme}'. Supported schemes are: {', '.join(SUPPORTED_SCHEMES)}"
        )

    # Normalize standard postgresql:// or legacy postgres:// to postgresql+psycopg2:// for psycopg2 driver
    if scheme == "postgres":
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif scheme == "postgresql":
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    return url


# Validate and normalize database URL
DATABASE_URL = validate_database_url(settings.DATABASE_URL)

# Configure connection arguments per dialect
connect_args = {}
engine_kwargs = {
    "pool_pre_ping": True,
}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    from sqlalchemy.pool import StaticPool
    engine_kwargs["poolclass"] = StaticPool
else:
    # PostgreSQL pooling configuration
    engine_kwargs.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_recycle": 1800,
            "pool_timeout": 30,
        }
    )

try:
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        **engine_kwargs,
    )
except Exception as exc:
    logger.critical(f"Failed to initialize database engine: {exc}", exc_info=True)
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI request dependency for database session lifecycle."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for database sessions outside HTTP request cycle."""
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(f"Database session rolled back due to error: {exc}", exc_info=True)
        raise
    finally:
        db.close()


def ping_db(session: Session = None) -> bool:
    """Verify database connection liveliness."""
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True
    try:
        session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning(f"Database ping check failed: {exc}")
        return False
    finally:
        if close_session:
            session.close()
