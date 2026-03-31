from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # PostgreSQL
    postgres_url: str = "postgresql://localhost:5432/sakhatype"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = ""
    postgres_db: str = "sakhatype"

    database_name: str = "sakhatype"
    secret_key: str = "your-super-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    frontend_url: str = "http://localhost:5173"
    allowed_origins: str | None = None

    model_config = SettingsConfigDict(env_file=".env")

    def resolved_database_name(self) -> str:
        return self.postgres_db or self.database_name

    def resolved_postgres_dsn(self) -> str:
        """Build asyncpg-compatible DSN."""
        url = (self.postgres_url or "").strip()
        if url and (url.startswith("postgresql://") or url.startswith("postgres://")):
            return url

        password_part = f":{self.postgres_password}" if self.postgres_password else ""
        return (
            f"postgresql://{self.postgres_user}{password_part}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.resolved_database_name()}"
        )

    def cors_origins(self) -> list[str]:
        default_origins = [
            self.frontend_url,
            "https://sakhatype.ru",
            "https://www.sakhatype.ru",
            "http://sakhatype.ru",
            "http://www.sakhatype.ru",
            "http://localhost:5173",
            "http://localhost:3000",
        ]
        if not self.allowed_origins:
            return default_origins

        parsed = [item.strip() for item in self.allowed_origins.split(",") if item.strip()]
        if not parsed:
            return default_origins

        merged: list[str] = []
        for origin in [*parsed, *default_origins]:
            if origin not in merged:
                merged.append(origin)
        return merged


@lru_cache()
def get_settings() -> Settings:
    return Settings()
