from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env.test", override=True)

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import GameMode

GAME_MODES = [
    {"slug": "classic", "display_name": "Classic"},
    {"slug": "energy", "display_name": "Energy"},
]

# A dedicated engine for tests, not the app's module-level `engine` singleton.
# Each pytest-asyncio test function gets its own event loop, and a pooled
# connection reused across loops breaks (asyncpg ties its socket transport to
# the loop it was created on). NullPool makes every `connect()` open a fresh
# connection instead of reusing one from a prior test's now-closed loop.
test_engine = create_async_engine(get_settings().database_url, poolclass=NullPool)


@pytest_asyncio.fixture
async def db_session():
    async with test_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
        await session.execute(insert(GameMode), GAME_MODES)
        await session.commit()  # goes through a SAVEPOINT, not a real commit

        yield session

        await session.close()
        await trans.rollback()  # undoes everything, including the seed insert


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
