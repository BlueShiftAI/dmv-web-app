"""
Application settings using Pydantic BaseSettings.
Values are read from environment variables / .env file.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+psycopg2://dmvapp:changeme@db:5432/dmvdb"

    # JWT
    secret_key: str = "insecure-dev-secret-replace-in-production"
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Uploads
    upload_dir: str = "/app/uploads"
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB

    # App
    demo_mode: bool = True
    app_env: str = "development"
    log_level: str = "INFO"
    timezone: str = "America/New_York"

    # Orchestrate (optional)
    orchestrate_api_key: str | None = None
    orchestrate_instance_url: str | None = None
    orchestrate_agent_id: str | None = None

    # Web Push VAPID (optional)
    vapid_public_key: str | None = None
    vapid_private_key: str | None = None
    vapid_mailto: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def orchestrate_enabled(self) -> bool:
        return bool(self.orchestrate_api_key and self.orchestrate_agent_id)


settings = Settings()
