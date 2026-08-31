from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.result import ErrorCode
from app.schemas import LeaderboardEntry, ScoreOut, ScoreSubmit
from app.services import leaderboard_service

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

_ERROR_STATUS = {
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.VALIDATION: 422,
}


async def _resolve_game_mode_id(slug: str, db: AsyncSession) -> int:
    result = await leaderboard_service.get_game_mode_by_slug(db, slug)
    if not result.success or result.value is None:
        assert result.error_code is not None
        raise HTTPException(
            status_code=_ERROR_STATUS[result.error_code], detail=result.error_message
        )
    return result.value.id


@router.post("/scores", response_model=ScoreOut, status_code=201)
async def submit_score(payload: ScoreSubmit, db: AsyncSession = Depends(get_db)):
    game_mode_id = await _resolve_game_mode_id(payload.game_mode, db)
    result = await leaderboard_service.submit_score(
        db, payload.name, payload.value, game_mode_id
    )
    if not result.success:
        assert result.error_code is not None
        raise HTTPException(
            status_code=_ERROR_STATUS[result.error_code], detail=result.error_message
        )
    return result.value


@router.get("/top", response_model=list[LeaderboardEntry])
async def get_top(
    mode: str = Query(...),
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    game_mode_id = await _resolve_game_mode_id(mode, db)
    result = await leaderboard_service.get_top_scores(db, game_mode_id, limit)
    return result.value
