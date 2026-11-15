import os

# Protect the project's jamt.db before app.main is imported:
#   * JAMT_SKIP_DB_INIT  -> app.main does not run ensure_schema() on import.
#   * JAMT_DATABASE_URL  -> the engine points at an in-memory database, so even
#                           an accidental write can never reach the local file.
# The automated tests therefore always run against isolated, in-memory storage.
os.environ["JAMT_SKIP_DB_INIT"] = "1"
os.environ["JAMT_DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app, Base, get_db


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine_test)


@pytest.fixture(autouse=True)
def disable_real_llm_calls(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def ac():
    """Sync test client using httpx for better session persistence."""
    test_session = TestingSessionLocal()
    # Override get_db to use this session for the entire test context
    app.dependency_overrides[get_db] = lambda: test_session
    try:
        with TestClient(app) as client:
            yield client
    finally:
        del app.dependency_overrides[get_db]
        test_session.close()
