"""X Interaction Agent for the OpenAI Agents SDK."""

import logging
from typing import Any, Optional

from agents import Agent, function_tool
from tools.x_api_tools import post_text_tweet as _post_text_tweet

logger = logging.getLogger(__name__)


@function_tool
def post_text_tweet(text: str, in_reply_to_tweet_id: Optional[str] = None) -> dict[str, Any]:
    """Post a text-only tweet using the X API v2.

    Args:
        text: The text content of the tweet.
        in_reply_to_tweet_id: Optional tweet ID to reply to.

    Returns:
        A dict containing the created tweet data.

    Raises:
        OAuthError: If authentication fails.
        XApiError: If the tweet creation fails.
    """
    result = _post_text_tweet(text=text, in_reply_to_tweet_id=in_reply_to_tweet_id)
    return result


class XInteractionAgent(Agent):
    """Agent specialized in interacting with the X platform by posting tweets."""

    def __init__(self) -> None:
        super().__init__(
            name="X Interaction Agent",
            instructions=(
                """
                You are the **X Interaction Agent** for AIified.

                ─── ROLE & OBJECTIVE ───
                Publish tweets provided by higher-level agents exactly as given (unless they violate policy).

                ─── PERSISTENCE REMINDER ───
                Keep going until the tweet has been successfully published with `post_text_tweet`.

                ─── TOOL-CALLING REMINDER ───
                • ALWAYS call the `post_text_tweet` tool – never respond with plain text.
                • If you lack required parameters, request them instead of guessing.

                ─── POLICY & VALIDATION ───
                • Ensure text ≤ 280 characters.
                • If it contains disallowed content (harassment, hate, sensitive categories), abort and return: `POLICY_BLOCK: <reason>`.

                ─── OUTPUT FORMAT ───
                • On success: return ONLY the raw JSON result from the tool call.
                • On policy block: return the `POLICY_BLOCK:` message.
                """
            ),
            model="gpt-4.1-nano",
            tools=[post_text_tweet],
        )
