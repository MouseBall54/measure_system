"""Application configuration via Pydantic settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings."""

    app_name: str = "Measure System API"
    environment: Literal["local", "staging", "production"] = "local"

    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "measure_user"
    mysql_password: str = "power123!"
    mysql_db: str = "measure_system"

    echo_sql: bool = False
    log_dir: str = "logs"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    @property
    def sqlalchemy_url(self) -> str:
        """Return the SQLAlchemy async MySQL connection string."""

        return (
            f"mysql+asyncmy://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


settings = get_settings()
