import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GameMode(Base):
    """
    Lookup table for the game's independent leaderboards, e.g. classic,
    energy. Scores reference this by id; the API takes/returns the slug.
    """

    __tablename__ = "game_modes"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(20), unique=True)
    display_name: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Score(Base):
    """
    One row per high-score entry — like an arcade cabinet's high score
    table. No account/login: whoever submits just types a name (or
    3-letter initials, arcade-style) alongside their score.
    """

    __tablename__ = "scores"
    # No secondary index on `value`: each game mode's scores are capped at
    # MAX_SCORES rows (see leaderboard_service), so a full scan within a
    # mode is cheap and an index would only add write cost.

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(20))  # arcade-style: keep it short, e.g. 3-letter initials
    value: Mapped[int] = mapped_column()  # store as int (points, ms) — avoid float drift
    game_mode_id: Mapped[int] = mapped_column(ForeignKey("game_modes.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
