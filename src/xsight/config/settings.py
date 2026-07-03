"""Global XSight configuration, loaded via Pydantic Settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings.

    Values may be overridden via environment variables prefixed with
    XSIGHT_ (e.g. XSIGHT_DB_PATH), or a .env file in the future.
    """

    model_config = SettingsConfigDict(env_prefix="XSIGHT_")

    db_path: Path = Path.home() / ".xsight" / "xsight.db"

    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "xsight_chunks"

settings = Settings()
