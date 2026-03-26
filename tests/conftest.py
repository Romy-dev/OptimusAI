"""Test configuration and shared fixtures."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.auth import create_access_token, hash_password
from app.core.database import get_session
from app.main import create_app
from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User, UserRole

# Use a separate test database
TEST_DATABASE_URL = settings.database_url.replace("/optimusai", "/optimusai_test")

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def setup_database():
    """Create tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def session() -> AsyncSession:
    async with TestSessionFactory() as session:
        yield session


@pytest.fixture
async def tenant(session: AsyncSession) -> Tenant:
    t = Tenant(
        name="Test Company",
        slug=f"test-{uuid.uuid4().hex[:6]}",
        is_active=True,
        settings={"language": "fr", "country": "BF"},
    )
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t


@pytest.fixture
async def user(session: AsyncSession, tenant: Tenant) -> User:
    u = User(
        tenant_id=tenant.id,
        email=f"test-{uuid.uuid4().hex[:6]}@test.com",
        hashed_password=hash_password("testpassword123"),
        full_name="Test User",
        role=UserRole.OWNER,
        is_active=True,
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


@pytest.fixture
def auth_token(user: User, tenant: Tenant) -> str:
    return create_access_token(user.id, tenant.id, user.role.value)


@pytest.fixture
async def client(session: AsyncSession, auth_token: str):
    """Async test client with auth."""
    app = create_app()

    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["Authorization"] = f"Bearer {auth_token}"
        yield ac
