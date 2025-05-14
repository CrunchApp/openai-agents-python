"""Core configuration module.

This module loads environment variables from a .env file and provides
application settings via a Pydantic BaseSettings class.
"""

from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseSettings, Field

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        openai_api_key: OpenAI API key.
        x_api_key: X API consumer key.
        x_api_secret_key: X API consumer secret.
        x_access_token: X API access token (optional).
        x_access_token_secret: X API access token secret (optional).
        x_bearer_token: X API bearer token for app-only auth (optional).
        log_level: Logging level.
        sqlite_db_path: Path to SQLite database file.
        token_encryption_key: Key for encrypting OAuth tokens in the database.
    """

    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    x_api_key: str = Field(..., env="X_API_KEY")
    x_api_secret_key: str = Field(..., env="X_API_SECRET_KEY")
    x_access_token: Optional[str] = Field(None, env="X_ACCESS_TOKEN")
    x_access_token_secret: Optional[str] = Field(None, env="X_ACCESS_TOKEN_SECRET")
    x_bearer_token: Optional[str] = Field(None, env="X_BEARER_TOKEN")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    sqlite_db_path: str = Field("data/agent_data.db", env="SQLITE_DB_PATH")
    token_encryption_key: str = Field(..., env="TOKEN_ENCRYPTION_KEY")

    class Config:
        """Pydantic configuration for settings."""
        case_sensitive = True


# Singleton settings instance for the application
settings = Settings() 