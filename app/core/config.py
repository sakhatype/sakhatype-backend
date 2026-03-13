from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_url: str | None = None
    mongodb_host: str = "localhost"
    mongodb_port: int = 27017
    mongodb_username: str | None = None
    mongodb_password: str | None = None
    mongodb_dbname: str | None = None
    mongodb_auth_source: str = "admin"

    database_name: str = "dotx_type"
    secret_key: str = "your-super-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    frontend_url: str = "http://localhost:5173"
    allowed_origins: str | None = None

    model_config = SettingsConfigDict(env_file=".env")

    def resolved_database_name(self) -> str:
        return self.mongodb_dbname or self.database_name

    def resolved_mongodb_url(self) -> str:
        if self.mongodb_url:
            return self.mongodb_url

        db_name = self.resolved_database_name()
        if self.mongodb_username and self.mongodb_password:
            username = quote_plus(self.mongodb_username)
            password = quote_plus(self.mongodb_password)
            auth_source = quote_plus(self.mongodb_auth_source)
            return (
                f"mongodb://{username}:{password}"
                f"@{self.mongodb_host}:{self.mongodb_port}/{db_name}"
                f"?authSource={auth_source}"
            )

        return f"mongodb://{self.mongodb_host}:{self.mongodb_port}"

    def cors_origins(self) -> list[str]:
        default_origins = [
            self.frontend_url,
            "https://sakhatype.ru",
            "http://sakhatype.ru",
            "http://localhost:5173",
            "http://localhost:3000",
        ]
        if not self.allowed_origins:
            return default_origins

        parsed = [item.strip() for item in self.allowed_origins.split(",") if item.strip()]
        return parsed or default_origins


@lru_cache()
def get_settings() -> Settings:
    return Settings()
