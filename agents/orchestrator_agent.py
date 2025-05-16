"""Orchestrator agent module for managing workflows."""

import logging
from agents import Agent, ModelSettings
from .x_interaction_agent import XInteractionAgent
from .content_creation_agent import ContentCreationAgent
from tools.x_api_tools import get_mentions, XApiError, post_text_tweet as _post_text_tweet
from core.oauth_manager import OAuthError
from tools.human_handoff_tool import request_human_review
from core.db_manager import get_agent_state, save_agent_state


class OrchestratorAgent(Agent):
    """Central coordinator agent for managing X platform interactions."""

    def __init__(self) -> None:
        """Initialize the Orchestrator Agent with logger and sub-agents."""
        super().__init__(
            name="Orchestrator Agent",
            instructions=(
                "You are a master orchestrator agent. Your role is to manage workflows "
                "involving other specialized agents and tools to manage an X account. "
                "You will decide when to fetch mentions, draft replies, request human review, and post content."
            ),
            model="o4-mini",
            model_settings=ModelSettings(temperature=0.5),
            tools=[],
        )
        self.logger = logging.getLogger(__name__)
        self.content_creation_agent = ContentCreationAgent()
        self.x_interaction_agent = XInteractionAgent()

    def run_simple_post_workflow(self, content: str) -> None:
        """Run a simple workflow that posts content to X via direct tool call."""
        self.logger.info("Starting simple post workflow (direct tool call).")
        try:
            result = _post_text_tweet(text=content)
            self.logger.info("Workflow completed successfully with result: %s", result)
        except Exception as e:
            self.logger.error("Workflow failed: %s", e)
            raise

    def process_new_mentions_workflow(self) -> None:
        """Process new mentions workflow: fetch mentions, draft replies, and request human review."""
        self.logger.info("Starting process new mentions workflow.")
        # Fetch last processed mention ID
        since_id = get_agent_state("last_processed_mention_id_default_user")
        try:
            mentions_response = get_mentions(since_id=since_id)
        except (XApiError, OAuthError) as e:
            self.logger.error("Failed to fetch new mentions: %s", e)
            return
        mentions_data = mentions_response.get("data", [])
        if not mentions_data:
            self.logger.info("No new mentions found.")
            return
        # Determine newest mention ID from meta or data
        newest_id = mentions_response.get("meta", {}).get("newest_id")
        if not newest_id:
            try:
                newest_id = max(m.get("id") for m in mentions_data)
            except Exception:
                newest_id = None
        content_agent = self.content_creation_agent
        for mention in mentions_data:
            mention_text = mention.get("text", "")
            mention_id = mention.get("id")
            author_id = mention.get("author_id")
            try:
                drafted = content_agent.draft_reply(
                    original_tweet_text=mention_text,
                    original_tweet_author=author_id,
                    mention_tweet_id=mention_id,
                )
                review_result = request_human_review(
                    task_type="reply_to_mention",
                    data_for_review=drafted,
                    reason="New mention reply drafted",
                )
                self.logger.info("Human review requested: %s", review_result)
            except Exception as e:
                self.logger.error(
                    "Failed to process mention %s: %s", mention_id, e
                )
        if newest_id:
            save_agent_state("last_processed_mention_id_default_user", newest_id)
        self.logger.info("Completed process new mentions workflow.") 