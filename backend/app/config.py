from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    cache_ttl_seconds: int = 60
    cors_origins: str = (
        "http://localhost:8080,http://localhost:5173,"
        "http://127.0.0.1:8080,http://127.0.0.1:5173"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def cors_origin_list(raw: str) -> list[str]:
    return [o.strip() for o in raw.split(",") if o.strip()]
