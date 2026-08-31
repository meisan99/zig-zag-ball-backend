import asyncio

from sqlalchemy.dialects.postgresql import insert

from app.database import async_session_maker
from app.models import GameMode

GAME_MODES = [
    {"slug": "classic", "display_name": "Classic"},
    {"slug": "energy", "display_name": "Energy"},
]


async def seed_game_modes():
    async with async_session_maker() as session:
        stmt = insert(GameMode).on_conflict_do_nothing(index_elements=["slug"])
        await session.execute(stmt, GAME_MODES)
        await session.commit()


async def main():
    await seed_game_modes()
    print("Game modes seeded.")


if __name__ == "__main__":
    asyncio.run(main())
