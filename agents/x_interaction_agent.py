"""X Interaction Agent for the OpenAI Agents SDK."""
import logging
from typing import Dict, Any

from agents import Agent, function_tool
from tools.x_api_tools import post_text_tweet as _post_text_tweet

logger = logging.getLogger(__name__)

@function_tool
def post_text_tweet(text: str) -> Dict[str, Any]:
    """Post a text-only tweet using the X API v2.

    Args:
        text: The text content of the tweet.

    Returns:
        A dict containing the created tweet data.

    Raises:
        OAuthError: If authentication fails.
        XApiError: If the tweet creation fails.
    """
    result = _post_text_tweet(text=text)
    return result


class XInteractionAgent(Agent):
    """Agent specialized in interacting with the X platform by posting tweets."""

    def __init__(self) -> None:
        super().__init__(
            name="X Interaction Agent",
            instructions=(
                "You are an agent specialized in interacting with the X platform. "
                "Use the provided tool to post tweets."
            ),
            model="gpt-4.1-nano",
            tools=[post_text_tweet],
        ) 