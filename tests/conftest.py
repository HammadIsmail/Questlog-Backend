"""
Shared pytest fixtures for the Questlog backend test suite.
Uses an in-memory SQLite database so tests run without a live PostgreSQL instance.
"""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Override DATABASE_URL before importing the app
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("GROQ_API_KEY", "gsk_test")
os.environ.setdefault("ASSEMBLYAI_API_KEY", "test-assemblyai-key")

from app.db.base import Base
from app.db.session import get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create an in-memory SQLite engine and initialize all tables."""
    from sqlalchemy.pool import StaticPool
    engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Per-test async database session with rollback on teardown."""
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(test_engine):
    """Async HTTP client bound to the FastAPI ASGI app with overridden DB dependency."""
    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Register a test user, log in, and return Authorization headers."""
    payload = {
        "email": "testuser@questlog.com",
        "name": "Test Adventurer",
        "password": "StrongPass123!",
    }
    # Register (ignore if already exists)
    await client.post("/api/v1/auth/register", json=payload)
    # Login
    resp = await client.post("/api/v1/auth/login", json={
        "email": payload["email"],
        "password": payload["password"],
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
