"""Temporary script to save initial X OAuth tokens for testing.

This script is for developer use only to manually insert pre-obtained tokens
into the database.
"""

from datetime import datetime, timedelta, timezone

from core.config import settings
from core.oauth_manager import save_tokens


def main() -> None:
    """Save pre-obtained OAuth tokens into the database for a user."""
    # Validate encryption key presence
    assert settings.token_encryption_key, "TOKEN_ENCRYPTION_KEY must be set in .env"

    # Placeholder values - replace these with actual tokens and values
    user_x_id: str = "default_user"
    access_token: str = "cHpfUFg2YlA4dkdZdjJrRFBybE94UE9YVlBsaXhaMTk0dmNnbzRVRGxPczlZOjE3NDc2Njg2Mzg4OTk6MToxOmF0OjE"
    refresh_token: str = "dlBfQUFLeE1fOW13RWNRUzdaem5FVXQ3dUxHSkdLZVF2Y3I0Z0w5aHljMW1VOjE3NDc2Njg2Mzg4OTk6MTowOnJ0OjE"
    expires_in_seconds: int = 7200  # e.g., 1 hour
    scopes_list: list[str] = [
        "tweet.read",
        "tweet.write",
        "users.read",
        "offline.access",
    ]

    # Calculate expiry datetime in UTC
    expires_at: datetime = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)

    # Save the tokens
    save_tokens(
        user_x_id=user_x_id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        scopes=scopes_list,
    )

    print(
        f"Successfully saved tokens for user '{user_x_id}' with expiry at {expires_at.isoformat()}"
    )


if __name__ == "__main__":
    main()
