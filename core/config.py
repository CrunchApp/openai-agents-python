# core/config.py
import os
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict  # Import SettingsConfigDict

# Ensure .env is loaded FIRST, populating os.environ
load_dotenv()

# --- DEBUG ---
print("--- DEBUG: Environment Variables after load_dotenv() ---")
print(f"OPENAI_API_KEY from os.getenv: {os.getenv('OPENAI_API_KEY')}")
print(f"X_API_KEY from os.getenv: {os.getenv('X_API_KEY')}")
print(f"X_API_SECRET_KEY from os.getenv: {os.getenv('X_API_SECRET_KEY')}")
print(f"TOKEN_ENCRYPTION_KEY from os.getenv: {os.getenv('TOKEN_ENCRYPTION_KEY')}")
print(f"LOG_LEVEL from os.getenv: {os.getenv('LOG_LEVEL')}")
print(f"SQLITE_DB_PATH from os.getenv: {os.getenv('SQLITE_DB_PATH')}")
print(f"X_CUA_USER_DATA_DIR from os.getenv: {os.getenv('X_CUA_USER_DATA_DIR')}")
print("--- END DEBUG ---")
# --- END DEBUG ---


class Settings(BaseSettings):
    # Pydantic will automatically look for environment variables
    # matching these field names (case-insensitively by default, but our Config makes it sensitive).
    # The `env` parameter in `Field` is technically redundant if the field name matches the env var name.
    # However, it's good for explicit mapping if they differ. Since they match, it should work.

    openai_api_key: str = Field(..., validation_alias="OPENAI_API_KEY")  # Using alias for clarity
    x_api_key: str = Field(..., validation_alias="X_API_KEY")
    x_api_secret_key: str = Field(..., validation_alias="X_API_SECRET_KEY")
    token_encryption_key: str = Field(..., validation_alias="TOKEN_ENCRYPTION_KEY")

    x_access_token: Optional[str] = Field(None, validation_alias="X_ACCESS_TOKEN")
    x_access_token_secret: Optional[str] = Field(None, validation_alias="X_ACCESS_TOKEN_SECRET")
    x_bearer_token: Optional[str] = Field(None, validation_alias="X_BEARER_TOKEN")

    # CUA Configuration
    x_cua_user_data_dir: Optional[str] = Field(None, validation_alias="X_CUA_USER_DATA_DIR")

    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")
    sqlite_db_path: str = Field("data/agent_data.db", validation_alias="SQLITE_DB_PATH")

    # This tells pydantic-settings how to load settings
    model_config = SettingsConfigDict(
        env_file=None,  # Explicitly disable pydantic-settings' own .env loading
        case_sensitive=True,
        extra="ignore",  # Ignore extra environment variables not defined in Settings
    )


# Singleton settings instance for the application
settings = Settings()
