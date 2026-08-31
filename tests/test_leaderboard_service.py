from typing import TypeVar

from sqlalchemy import select

from app.models import Score
from app.result import ErrorCode, Result
from app.services import leaderboard_service

T = TypeVar("T")


def _unwrap(result: Result[T]) -> T:
    assert result.success, result.error_message
    assert result.value is not None
    return result.value


async def _get_mode_id(db_session, slug: str) -> int:
    result = await leaderboard_service.get_game_mode_by_slug(db_session, slug)
    return _unwrap(result).id


async def test_get_game_mode_by_slug_found(db_session):
    result = await leaderboard_service.get_game_mode_by_slug(db_session, "classic")
    assert _unwrap(result).slug == "classic"


async def test_get_game_mode_by_slug_not_found(db_session):
    result = await leaderboard_service.get_game_mode_by_slug(db_session, "nonexistent")
    assert not result.success
    assert result.error_code == ErrorCode.NOT_FOUND


async def test_submit_score_success(db_session):
    game_mode_id = await _get_mode_id(db_session, "classic")
    result = await leaderboard_service.submit_score(db_session, "AAA", 100, game_mode_id)
    score = _unwrap(result)
    assert score.name == "AAA"
    assert score.value == 100
    assert score.game_mode_id == game_mode_id


async def test_submit_score_rejects_profanity(db_session):
    game_mode_id = await _get_mode_id(db_session, "classic")
    result = await leaderboard_service.submit_score(db_session, "fuck", 100, game_mode_id)
    assert not result.success
    assert result.error_code == ErrorCode.VALIDATION


async def test_submit_score_prunes_to_cap(db_session):
    game_mode_id = await _get_mode_id(db_session, "classic")

    for i in range(leaderboard_service.MAX_SCORES):
        result = await leaderboard_service.submit_score(db_session, f"S{i}", i + 1, game_mode_id)
        assert result.success

    rows = (
        await db_session.execute(select(Score).where(Score.game_mode_id == game_mode_id))
    ).scalars().all()
    assert len(rows) == leaderboard_service.MAX_SCORES

    # A new high score should qualify and push out the current lowest (value=1).
    result = await leaderboard_service.submit_score(db_session, "NEW", 9999, game_mode_id)
    assert result.success

    rows = (
        await db_session.execute(select(Score).where(Score.game_mode_id == game_mode_id))
    ).scalars().all()
    assert len(rows) == leaderboard_service.MAX_SCORES
    values = {row.value for row in rows}
    assert 9999 in values
    assert 1 not in values


async def test_submit_score_low_value_does_not_survive_when_full(db_session):
    game_mode_id = await _get_mode_id(db_session, "classic")

    for i in range(leaderboard_service.MAX_SCORES):
        result = await leaderboard_service.submit_score(db_session, f"S{i}", i + 100, game_mode_id)
        assert result.success

    result = await leaderboard_service.submit_score(db_session, "LOW", 1, game_mode_id)
    assert result.success  # the insert itself succeeds...

    rows = (
        await db_session.execute(
            select(Score).where(Score.game_mode_id == game_mode_id, Score.name == "LOW")
        )
    ).scalars().all()
    assert rows == []  # ...but it's immediately pruned out


async def test_get_top_scores_orders_highest_first(db_session):
    game_mode_id = await _get_mode_id(db_session, "classic")
    await leaderboard_service.submit_score(db_session, "LOW", 10, game_mode_id)
    await leaderboard_service.submit_score(db_session, "HIGH", 50, game_mode_id)
    await leaderboard_service.submit_score(db_session, "MID", 30, game_mode_id)

    result = await leaderboard_service.get_top_scores(db_session, game_mode_id, limit=10)
    entries = _unwrap(result)
    assert [e.name for e in entries] == ["HIGH", "MID", "LOW"]
    assert [e.rank for e in entries] == [1, 2, 3]


async def test_get_top_scores_respects_limit(db_session):
    game_mode_id = await _get_mode_id(db_session, "classic")
    for i in range(5):
        await leaderboard_service.submit_score(db_session, f"P{i}", i + 1, game_mode_id)

    result = await leaderboard_service.get_top_scores(db_session, game_mode_id, limit=2)
    assert len(_unwrap(result)) == 2


async def test_get_top_scores_tie_break_by_earliest(db_session):
    game_mode_id = await _get_mode_id(db_session, "classic")
    first = await leaderboard_service.submit_score(db_session, "FIRST", 100, game_mode_id)
    second = await leaderboard_service.submit_score(db_session, "SECOND", 100, game_mode_id)
    assert first.success and second.success

    result = await leaderboard_service.get_top_scores(db_session, game_mode_id, limit=10)
    entries = _unwrap(result)
    assert [e.name for e in entries] == ["FIRST", "SECOND"]


async def test_scores_are_isolated_per_game_mode(db_session):
    classic_id = await _get_mode_id(db_session, "classic")
    energy_id = await _get_mode_id(db_session, "energy")

    await leaderboard_service.submit_score(db_session, "C1", 100, classic_id)
    await leaderboard_service.submit_score(db_session, "E1", 200, energy_id)

    classic_top = _unwrap(await leaderboard_service.get_top_scores(db_session, classic_id, limit=10))
    energy_top = _unwrap(await leaderboard_service.get_top_scores(db_session, energy_id, limit=10))

    assert [e.name for e in classic_top] == ["C1"]
    assert [e.name for e in energy_top] == ["E1"]
