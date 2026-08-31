import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ScoreSubmit(BaseModel):
    name: str = Field(min_length=1, max_length=20)  # e.g. 3-letter arcade initials, or a full name
    value: int = Field(gt=0, le=2_147_483_647)  # fits Postgres int4, matches the `value` column
    game_mode: str = Field(min_length=1, max_length=20)  # slug, e.g. "classic", "energy"


class ScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    value: int
    game_mode_id: int
    created_at: datetime


class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    value: int


class ErrorResponse(BaseModel):
    error_code: str
    message: str
