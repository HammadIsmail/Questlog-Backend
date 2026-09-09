from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/dungeon_master"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    algorithm: str = "HS256"

    # AI Providers
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    assemblyai_api_key: str = ""

    # App
    app_env: str = "development"
    # Typed as Union so pydantic-settings won't attempt json.loads on comma-separated values
    allowed_origins: Union[List[str], str] = ["http://localhost", "http://127.0.0.1", "http://localhost:3000"]

    @property
    def cors_origins(self) -> List[str]:
        """Return allowed origins as a clean list of strings."""
        val = self.allowed_origins
        if isinstance(val, str):
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                try:
                    return json.loads(val)
                except Exception:
                    pass
            return [origin.strip() for origin in val.split(",") if origin.strip()]
        return val

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def normalized_database_url(self) -> str:
        """Ensure PostgreSQL connection strings use asyncpg driver and clean incompatible params."""
        url = self.database_url.strip()
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        elif url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://"):]
        
        # asyncpg prefers ssl=require rather than sslmode=require and doesn't support channel_binding
        if "sslmode=" in url:
            url = url.replace("sslmode=require", "ssl=require")
        if "&channel_binding=require" in url:
            url = url.replace("&channel_binding=require", "")
        elif "?channel_binding=require" in url:
            url = url.replace("?channel_binding=require", "")

        return url


settings = Settings()
