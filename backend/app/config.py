from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache
import json


class Settings(BaseSettings):
    # External URL
    EXTERNAL_URL: str = "http://localhost:8000"

    # Database settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "password"
    DB_NAME: str = "fastapi_db"

    # API settings
    APICURIO_URL: str = "http://localhost:8080"

    # Schema settings (JSON-formatted list)
    SCHEMAS: List[str] = []

    class Config:
        env_file = ".env"

    @property
    def DATABASE_URL(self) -> str:
        """Generate the database URL from component parts."""
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @classmethod
    def parse_schemas(cls, v):
        """Parse the SCHEMAS field from a JSON string."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v or []


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
