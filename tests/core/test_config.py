import pytest
from pydantic import ValidationError

from core.config import Settings


def test_log_level_default(monkeypatch):
    """Test that log_level defaults to 'INFO' when LOG_LEVEL is not set."""
    # Ensure LOG_LEVEL is not set
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    # Set other required environment variables
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
    monkeypatch.setenv("X_API_KEY", "test_x_key")
    monkeypatch.setenv("X_API_SECRET_KEY", "test_x_secret")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "test_token_enc")
    settings = Settings()
    assert settings.log_level == "INFO"


def test_missing_required_env_vars(monkeypatch):
    """Test that missing required environment variables raises ValidationError."""
    # Ensure required environment variables are not set
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("X_API_KEY", raising=False)
    monkeypatch.delenv("X_API_SECRET_KEY", raising=False)
    monkeypatch.delenv("TOKEN_ENCRYPTION_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings()


def test_loading_env_vars(monkeypatch):
    """Test that Settings loads environment variables correctly."""
    # Set required environment variables
    monkeypatch.setenv("OPENAI_API_KEY", "env_openai_key")
    monkeypatch.setenv("X_API_KEY", "env_x_key")
    monkeypatch.setenv("X_API_SECRET_KEY", "env_x_secret")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "env_token_enc")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("SQLITE_DB_PATH", "custom.db")
    settings = Settings()
    assert settings.openai_api_key == "env_openai_key"
    assert settings.x_api_key == "env_x_key"
    assert settings.x_api_secret_key == "env_x_secret"
    assert settings.token_encryption_key == "env_token_enc"
    assert settings.log_level == "DEBUG"
    assert settings.sqlite_db_path == "custom.db"
    # Optional settings default to None
    assert settings.x_access_token is None
    assert settings.x_access_token_secret is None
    assert settings.x_bearer_token is None
