"""
Module for managing X API OAuth2 tokens with PKCE: encryption, storage, retrieval, refresh logic, and utility function for obtaining valid tokens.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
from cryptography.fernet import Fernet, InvalidToken

from core.config import settings
from core.db_manager import get_oauth_tokens, save_oauth_tokens

# Initialize logger for this module
debug_logger = logging.getLogger(__name__)


class OAuthError(Exception):
    """Custom exception for OAuth manager errors."""

    pass


def _get_fernet() -> Fernet:
    """Create a Fernet instance using the configured encryption key."""
    try:
        key = settings.token_encryption_key
        key_bytes = key.encode() if isinstance(key, str) else key
        return Fernet(key_bytes)
    except Exception as e:
        debug_logger.error("Failed to create Fernet instance: %s", e)
        raise OAuthError("Invalid token encryption key") from e


def _encrypt_token(token: str) -> str:
    """Encrypt a token string and return its ciphertext."""
    f = _get_fernet()
    try:
        encrypted_bytes = f.encrypt(token.encode())
        return encrypted_bytes.decode()
    except Exception as e:
        debug_logger.error("Token encryption failed: %s", e)
        raise OAuthError("Token encryption failed") from e


def _decrypt_token(encrypted_token: str) -> str:
    """Decrypt an encrypted token string and return the plaintext."""
    f = _get_fernet()
    try:
        decrypted_bytes = f.decrypt(encrypted_token.encode())
        return decrypted_bytes.decode()
    except InvalidToken as e:
        debug_logger.error("Invalid token for decryption: %s", e)
        raise OAuthError("Invalid encrypted token") from e
    except Exception as e:
        debug_logger.error("Token decryption failed: %s", e)
        raise OAuthError("Token decryption failed") from e


def save_tokens(
    user_x_id: str,
    access_token: str,
    refresh_token: Optional[str],
    expires_at: datetime,
    scopes: list[str],
) -> None:
    """Encrypt and save OAuth tokens to the database for a given user.

    Args:
        user_x_id: The X user ID or identifier.
        access_token: The OAuth2 access token.
        refresh_token: The OAuth2 refresh token (if any).
        expires_at: Expiry timestamp for the access token.
        scopes: List of granted scopes.

    Raises:
        OAuthError: If encryption or database save fails.
    """
    encrypted_access = _encrypt_token(access_token)
    encrypted_refresh = _encrypt_token(refresh_token) if refresh_token else None
    expires_at_iso = expires_at.isoformat()
    scopes_str = " ".join(scopes)
    try:
        save_oauth_tokens(
            user_x_id=user_x_id,
            access_token=encrypted_access,
            refresh_token=encrypted_refresh,
            expires_at=expires_at_iso,
            scopes=scopes_str,
        )
    except Exception as e:
        debug_logger.error("Failed to save tokens for user %s: %s", user_x_id, e)
        raise OAuthError("Failed to save tokens") from e


def get_tokens(
    user_x_id: str = "default_user",
) -> tuple[str, Optional[str], datetime, list[str]]:
    """Retrieve and decrypt the latest tokens for a user.

    Args:
        user_x_id: The X user ID or identifier.

    Returns:
        A tuple of (access_token, refresh_token, expires_at, scopes).

    Raises:
        OAuthError: If retrieval or decryption fails, or no tokens exist.
    """
    try:
        row = get_oauth_tokens(user_x_id=user_x_id)
        if not row:
            raise OAuthError(f"No tokens found for user {user_x_id}")
        encrypted_access = row["access_token"]
        encrypted_refresh = row["refresh_token"]
        expires_at_iso = row["expires_at"]
        scopes_str = row["scopes"]

        access_token = _decrypt_token(encrypted_access)
        refresh_token = _decrypt_token(encrypted_refresh) if encrypted_refresh else None
        expires_at_dt = datetime.fromisoformat(expires_at_iso)
        if scopes_str:
            scopes = [s for s in scopes_str.strip().split(" ") if s]
        else:
            scopes = []
        return access_token, refresh_token, expires_at_dt, scopes
    except OAuthError:
        raise
    except Exception as e:
        debug_logger.error("Failed to retrieve tokens for user %s: %s", user_x_id, e)
        raise OAuthError("Failed to retrieve tokens") from e


def refresh_access_token(user_x_id: str = "default_user") -> str:
    """Refresh the access token using the stored refresh token.

    Args:
        user_x_id: The X user ID or identifier.

    Returns:
        The new access token.

    Raises:
        OAuthError: If refresh fails or no refresh token is available.
    """
    access_token, refresh_token, expires_at, scopes = get_tokens(user_x_id)
    if not refresh_token:
        raise OAuthError("No refresh token available to refresh access token.")

    token_url = "https://api.twitter.com/2/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": settings.x_api_key,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = requests.post(token_url, data=data, headers=headers)
        if response.status_code != 200:
            debug_logger.error(
                "Token refresh failed for user %s: %s - %s",
                user_x_id,
                response.status_code,
                response.text,
            )
            raise OAuthError(f"Token refresh failed: {response.status_code}")
        token_data = response.json()
        new_access = token_data["access_token"]
        # Use new_refresh if returned, else fallback to existing
        new_refresh = token_data.get("refresh_token", refresh_token)
        expires_in = token_data.get("expires_in")
        new_expires = (
            datetime.now(timezone.utc) + timedelta(seconds=expires_in) if expires_in else expires_at
        )
        scope_str = token_data.get("scope", " ".join(scopes))
        new_scopes = scope_str.split(" ") if scope_str else []

        # Persist updated tokens
        save_tokens(user_x_id, new_access, new_refresh, new_expires, new_scopes)
        return new_access
    except OAuthError:
        raise
    except Exception as e:
        debug_logger.error("Error refreshing token for user %s: %s", user_x_id, e)
        raise OAuthError("Error refreshing access token") from e


def get_valid_x_token(user_x_id: str = "default_user") -> str:
    """Get a valid access token, refreshing it if it's expired or near expiry.

    Args:
        user_x_id: The X user ID or identifier.

    Returns:
        A valid access token string.

    Raises:
        OAuthError: If token retrieval or refresh fails.
    """
    access_token, _, expires_at, _ = get_tokens(user_x_id)
    # If token is expired or will expire within 5 minutes, refresh
    if datetime.now(timezone.utc) + timedelta(minutes=5) >= expires_at:
        return refresh_access_token(user_x_id)
    return access_token
