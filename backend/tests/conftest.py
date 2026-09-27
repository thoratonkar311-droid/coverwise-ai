import os
from typing import Generator
import pytest

# Ensure safe in-memory test database strategy before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.models  # Ensure all models are registered with Base.metadata before app loads
from app.db.session import Base, SessionLocal, engine
from app.main import app as fastapi_app


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all database schema tables for the test session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a fresh database session for tests with automatic cleanup."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """Session-scoped TestClient configured for the FastAPI application."""
    with TestClient(fastapi_app, raise_server_exceptions=False) as test_client:
        yield test_client
