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
                """
                You are the **Content Creation Agent** for the @AIified account on X (Twitter).

                TASK: Given an original mention (tweet text and author), craft a single reply tweet that:
                • Adds genuine value (answer a question, share a quick insight, or express appreciation).
                • Matches AIified's voice: friendly, knowledgeable, concise, professional.
                • Fits within 280 characters (hard limit). Aim for ≤ 240 chars to allow retweets.
                • Uses plain language; avoid heavy jargon. One emoji max (optional).
                • Mentions the original author with "@username". Do **not** reveal automation.
                • Avoid hashtags unless they meaningfully add discoverability (#AI, #MachineLearning, etc.).

                OUTPUT: Return ONLY the reply tweet text – no code fences, no additional commentary.
                """
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

    def draft_original_post(self, topic_summary: str, persona_prompt: str) -> dict[str, Any]:
        """Drafts an original tweet post for AIified based on a topic summary and persona instructions.

        Args:
            topic_summary: A summary of the topic to generate the tweet about.
            persona_prompt: Instructions defining the persona for the tweet.

        Returns:
            A dict containing the drafted tweet text, the source topic, and the status.
        """
        self.logger.info("Drafting original post for AIified based on topic: %s", topic_summary[:100])

        # Construct messages for OpenAI API client.responses.create
        # The persona_prompt will act as a system message for this specific generation
        # The topic_summary will be the user message.
        input_messages = [
            {"role": "system", "content": persona_prompt},
            {"role": "user", "content": f"Based on the following information, please draft an engaging and insightful tweet (max 280 chars):\n\n{topic_summary}"}
        ]
        try:
            response = self.client.responses.create( # Using existing self.client
                model="gpt-4.1", # Or another capable model for creative generation
                input=input_messages,
            )
            draft_text = response.output_text.strip()
            # Optional: Add basic validation for length, or let HIL catch it.
            # if len(draft_text) > 280:
            #     draft_text = draft_text[:277] + "..."
        except APIError as e:
            self.logger.error("OpenAI API error during draft_original_post: %s", e)
            draft_text = f"Error generating post on: {topic_summary[:50]}..."

        return {
            "draft_tweet_text": draft_text,
            "source_topic": topic_summary,
            "status": "drafted_for_review",
        }
