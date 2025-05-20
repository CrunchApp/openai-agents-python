"""Content creation agent for drafting replies to mentions.

This module defines the ContentCreationAgent which drafts replies
to mentions for human review.
"""

import logging
from typing import Any

from openai import APIError, OpenAI

from agents import Agent, ModelSettings
from core.config import settings


class ContentCreationAgent(Agent):
    """Agent for drafting content replies for mentions."""

    def __init__(self) -> None:
        """Initialize the ContentCreationAgent with a logger and OpenAI client."""
        super().__init__(
            name="Content Creation Agent",
            instructions=(
                "You are an AI assistant managing a Twitter account. "
                "Your task is to draft a concise, positive, and engaging reply to a given X mention. "
                "The user will provide the original tweet text and its author."
            ),
            model="gpt-4o",
            tools=[],  # This agent doesn't expose tools, its core is LLM generation
        )
        self.logger = logging.getLogger(__name__)
        self.client = OpenAI(api_key=settings.openai_api_key)

    def draft_reply(
        self,
        original_tweet_text: str,
        original_tweet_author: str,
        mention_tweet_id: str,
    ) -> dict[str, Any]:
        """Draft a reply to a given mention tweet for later human review.

        Args:
            original_tweet_text: The text of the tweet mentioning the agent.
            original_tweet_author: The username of the author of the original tweet.
            mention_tweet_id: The ID of the mention tweet.

        Returns:
            A dict containing the drafted reply text, the original mention ID,
            and the status.
        """
        self.logger.info(
            "Drafting reply to tweet ID %s from author @%s using SDK-compliant agent",
            mention_tweet_id,
            original_tweet_author,
        )
        # Prepare user input for the agent's LLM
        input_messages = [
            {
                "role": "system",
                "content": self.instructions
            },
            {
                "role": "user",
                "content": (f'Original tweet by @{original_tweet_author}: "{original_tweet_text}"'),
            }
        ]
        try:
            # Call the LLM using the agent's configured model and settings
            response = self.client.responses.create(
                model=self.model,
                input=input_messages,
            )
            reply_text = response.output_text.strip()
        except APIError as e:
            self.logger.error("OpenAI API error during draft_reply: %s", e)
            # Fallback to placeholder text on error
            reply_text = (
                f"Thank you @{original_tweet_author} for your tweet! "
                f"This is a drafted reply to '{original_tweet_text[:30]}...'."
            )
        return {
            "draft_reply_text": reply_text,
            "original_mention_id": mention_tweet_id,
            "status": "drafted_for_review",
        }
