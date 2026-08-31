from better_profanity import profanity
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GameMode, Score
from app.result import ErrorCode, Result
from app.schemas import LeaderboardEntry

# Hard cap on rows kept per game mode. Anything that falls below the cut is
# deleted on submit, so each mode's leaderboard stays small — like an arcade
# cabinet that only ever remembers its top 50.
MAX_SCORES = 50

# Ties broken by who got there first, so the retained set is deterministic.
_RANKING = (Score.value.desc(), Score.created_at.asc())


async def get_game_mode_by_slug(db: AsyncSession, slug: str) -> Result[GameMode]:
    row = await db.execute(
        select(GameMode).where(GameMode.slug == slug, GameMode.is_active.is_(True))
    )
    game_mode = row.scalar_one_or_none()
    if game_mode is None:
        return Result.fail(ErrorCode.NOT_FOUND, f"Unknown game mode: {slug!r}")
    return Result.ok(game_mode)


async def _prune_to_cap(db: AsyncSession, game_mode_id: int) -> None:
    """Delete everything outside the top MAX_SCORES for this game mode."""
    survivors = (
        select(Score.id)
        .where(Score.game_mode_id == game_mode_id)
        .order_by(*_RANKING)
        .limit(MAX_SCORES)
    )
    await db.execute(
        delete(Score).where(Score.game_mode_id == game_mode_id, Score.id.not_in(survivors))
    )


async def submit_score(
    db: AsyncSession, name: str, value: int, game_mode_id: int
) -> Result[Score]:
    if profanity.contains_profanity(name):
        return Result.fail(ErrorCode.VALIDATION, "Cannot accept vulgar terms")

    score = Score(name=name, value=value, game_mode_id=game_mode_id)
    db.add(score)

    # flush + refresh populates id/created_at (needed both for the response and
    # for the tie-break ordering) without ending the transaction.
    await db.flush()
    await db.refresh(score)

    # Same transaction as the insert, so the mode's rows are never above the
    # cap. A submission that doesn't make the top MAX_SCORES for its mode is
    # deleted right here; the response still describes it, since the session
    # is configured with expire_on_commit=False.
    await _prune_to_cap(db, game_mode_id)
    await db.commit()

    return Result.ok(score)


async def get_top_scores(
    db: AsyncSession, game_mode_id: int, limit: int = 10
) -> Result[list[LeaderboardEntry]]:
    # Highest value first. Flip to .asc() if lower-is-better (e.g. race times).
    rows = await db.execute(
        select(Score.name, Score.value)
        .where(Score.game_mode_id == game_mode_id)
        .order_by(*_RANKING)
        .limit(limit)
    )

    entries = [
        LeaderboardEntry(rank=i + 1, name=name, value=value)
        for i, (name, value) in enumerate(rows.all())
    ]
    return Result.ok(entries)
