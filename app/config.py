from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central app config, loaded from environment variables / .env.
    Mirrors the idea of a ScriptableObject config asset in Unity —
    one place to read runtime settings from, not scattered getenv() calls.
    """

    database_url: str
    environment: str = "local"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    # lru_cache means this only gets constructed once per process,
    # then reused — same idea as a lazy-initialized singleton.
    # The suppression below is for the type checker only: pydantic-settings
    # fills fields from the environment, which static analysis cannot see,
    # so it wrongly reports database_url as a missing argument.
    return Settings()  # type: ignore[call-arg]
