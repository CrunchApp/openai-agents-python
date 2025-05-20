"""X API tools module for interacting with Twitter via Tweepy."""

import logging
from typing import Any, Optional

import requests

from core.oauth_manager import OAuthError, get_valid_x_token

logger = logging.getLogger(__name__)


class XApiError(Exception):
    """Custom exception for X API request failures."""

    pass


def post_text_tweet(text: str, in_reply_to_tweet_id: Optional[str] = None) -> dict[str, Any]:
    """Post a text-only tweet using the X API v2.

    Args:
        text: The text content of the tweet.
        in_reply_to_tweet_id: Optional tweet ID to reply to.

    Returns:
        A dict containing the created tweet data.

    Raises:
        OAuthError: If retrieving or refreshing the X API token fails.
        XApiError: If the tweet creation request fails or response parsing fails.
    """
    try:
        access_token = get_valid_x_token(user_x_id="default_user")
    except OAuthError as e:
        logger.error("Failed to obtain valid X API token: %s", e)
        raise

    url = "https://api.twitter.com/2/tweets"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {"text": text}
    if in_reply_to_tweet_id:
        payload["reply"] = {"in_reply_to_tweet_id": in_reply_to_tweet_id}
    try:
        response = requests.post(url, headers=headers, json=payload)
    except Exception as e:
        logger.error("Error sending tweet request: %s", e)
        raise XApiError("Failed to send tweet request") from e

    if response.status_code != 201:
        logger.error(
            "Tweet creation failed: status %s, response %s", response.status_code, response.text
        )
        try:
            error_details = response.json()
            logger.error("Error details: %s", error_details)
        except Exception:
            pass
        raise XApiError(f"Tweet creation failed with status code {response.status_code}")

    try:
        data = response.json()
    except ValueError as e:
        logger.error("Failed to parse tweet response JSON: %s", e)
        raise XApiError("Failed to parse tweet response JSON") from e

    return data


def get_mentions(since_id: Optional[str] = None) -> dict[str, Any]:
    """Fetch mentions of the authenticated user's account from X API v2.

    Args:
        since_id: Optional ID string. If provided, fetch mentions newer than this Tweet ID.

    Returns:
        A dict containing tweet data, user objects, and metadata from the mentions endpoint.

    Raises:
        OAuthError: If token retrieval fails.
        XApiError: If the API request fails or response JSON parsing fails.
    """
    try:
        access_token = get_valid_x_token(user_x_id="default_user")
    except OAuthError as e:
        logger.error("Failed to obtain valid X API token for mentions: %s", e)
        raise

    # Get authenticated user's ID
    user_me_url = "https://api.twitter.com/2/users/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        user_resp = requests.get(user_me_url, headers=headers)
    except Exception as e:
        logger.error("Error fetching authenticated user info: %s", e)
        raise XApiError("Failed to fetch authenticated user information") from e

    if user_resp.status_code != 200:
        logger.error(
            "Failed to fetch authenticated user info: status %s, response %s",
            user_resp.status_code,
            user_resp.text,
        )
        raise XApiError(
            f"Failed to fetch authenticated user info with status code {user_resp.status_code}"
        )

    try:
        user_data = user_resp.json()
        user_id = user_data["data"]["id"]
    except Exception as e:
        logger.error("Error parsing authenticated user info JSON: %s", e)
        raise XApiError("Failed to parse authenticated user info response") from e

    # Fetch mentions for the user
    mentions_url = f"https://api.twitter.com/2/users/{user_id}/mentions"
    params: dict[str, Any] = {
        "tweet.fields": "created_at,author_id,text",
        "expansions": "author_id",
        "user.fields": "username,name",
        "max_results": 20,
    }
    if since_id:
        params["since_id"] = since_id

    try:
        resp = requests.get(mentions_url, headers=headers, params=params)
    except Exception as e:
        logger.error("Error fetching mentions: %s", e)
        raise XApiError("Failed to fetch mentions") from e

    if resp.status_code != 200:
        logger.error(
            "Mentions fetch failed: status %s, response %s",
            resp.status_code,
            resp.text,
        )
        try:
            error_details = resp.json()
            logger.error("Error details: %s", error_details)
        except Exception:
            pass
        raise XApiError(f"Mentions fetch failed with status code {resp.status_code}")

    try:
        data = resp.json()
    except ValueError as e:
        logger.error("Failed to parse mentions response JSON: %s", e)
        raise XApiError("Failed to parse mentions response JSON") from e

    return data
