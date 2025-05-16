"""Agent for interacting with the X platform using API tools."""

import logging
from typing import Dict, Any

from core.oauth_manager import OAuthError
from tweepy import TweepyException

from tools.x_api_tools import post_text_tweet


class XInteractionAgent:
    """Agent responsible for performing actions on the X platform."""

    def __init__(self) -> None:
        """Initialize the XInteractionAgent with a logger."""
        self._logger = logging.getLogger(__name__)

    def post_tweet(self, text_to_post: str) -> Dict[str, Any]:
        """Post a tweet to the X platform.

        Args:
            text_to_post: The content of the tweet to post.

        Returns:
            A dictionary containing the tweet data returned by the X API.

        Raises:
            OAuthError: If authentication fails.
            TweepyException: If the tweet creation fails.
            Exception: For any other unexpected errors.
        """
        self._logger.info("Attempting to post tweet.")
        try:
            result = post_text_tweet(text=text_to_post)
            self._logger.info("Tweet posted successfully: %s", result)
            return result
        except OAuthError as e:
            self._logger.error("OAuth error while posting tweet: %s", e)
            raise
        except TweepyException as e:
            self._logger.error("Tweepy error while posting tweet: %s", e)
            raise
        except Exception as e:
            self._logger.error("Unexpected error while posting tweet: %s", e)
            raise 