"""Orchestrator agent module for managing workflows."""

import json
import logging
from typing import Any

from agents import Agent, ModelSettings, RunContextWrapper, function_tool
from core.db_manager import (
    get_agent_state,
    get_approved_reply_tasks,
    save_agent_state,
    update_human_review_status,
)
from core.oauth_manager import OAuthError
from project_agents.content_creation_agent import ContentCreationAgent
from project_agents.x_interaction_agent import XInteractionAgent
from tools.human_handoff_tool import _request_human_review_impl as call_request_human_review, DraftedReplyData
from tools.x_api_tools import XApiError, get_mentions, post_text_tweet as _post_text_tweet
from pydantic import ValidationError


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
            tools=[],
        )
        self.logger = logging.getLogger(__name__)
        self.content_creation_agent = ContentCreationAgent()
        self.x_interaction_agent = XInteractionAgent()

        # Expose process_new_mentions_workflow as a tool for LLM-driven orchestration
        @function_tool(
            name_override="process_new_mentions",
            description_override="Process new X mentions: fetch mentions, draft replies, request human review, and update state",
        )
        async def _process_new_mentions_tool(ctx: RunContextWrapper[Any]) -> None:
            """Tool wrapper for process_new_mentions_workflow."""
            await self.process_new_mentions_workflow()

        self.tools.append(_process_new_mentions_tool)

        # Expose process_approved_replies_workflow as a tool for human-approved replies processing
        @function_tool(
            name_override="process_approved_replies",
            description_override="Process approved human-reviewed replies: post approved replies and update review status",
        )
        async def _process_approved_replies_tool(ctx: RunContextWrapper[Any]) -> None:
            """Tool wrapper for process_approved_replies_workflow."""
            await self.process_approved_replies_workflow()

        self.tools.append(_process_approved_replies_tool)

    def run_simple_post_workflow(self, content: str) -> None:
        """Run a simple workflow that posts content to X via direct tool call."""
        self.logger.info("Starting simple post workflow (direct tool call).")
        try:
            result = _post_text_tweet(text=content)
            self.logger.info("Workflow completed successfully with result: %s", result)
        except Exception as e:
            self.logger.error("Workflow failed: %s", e)
            raise

    async def process_new_mentions_workflow(self) -> None:
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
                drafted_dict = content_agent.draft_reply(
                    original_tweet_text=mention_text,
                    original_tweet_author=author_id,
                    mention_tweet_id=mention_id,
                )
                # Convert the drafted reply dict into a Pydantic model for strict schema
                try:
                    handoff_data = DraftedReplyData(**drafted_dict)
                except ValidationError as e_pydantic:
                    self.logger.error(f"Failed to create DraftedReplyData for mention {mention_id}: {e_pydantic}")
                    continue
                review_result = call_request_human_review(
                    task_type="reply_to_mention",
                    data_for_review=handoff_data,
                    reason="New mention reply drafted",
                )
                self.logger.info("Human review requested: %s", review_result)
            except Exception as e:
                self.logger.error("Failed to process mention %s: %s", mention_id, e)
        if newest_id:
            save_agent_state("last_processed_mention_id_default_user", newest_id)
        self.logger.info("Completed process new mentions workflow.")

    async def process_approved_replies_workflow(self) -> None:
        """Process approved replies workflow: fetch approved replies, post to X, and update review status."""
        self.logger.info("Starting process approved replies workflow.")
        try:
            tasks = get_approved_reply_tasks()
        except Exception as e:
            self.logger.error("Failed to fetch approved replies: %s", e)
            return
        if not tasks:
            self.logger.info("No approved replies to process.")
            return
        for task in tasks:
            review_id = task.get("review_id")
            data_json = task.get("data_for_review")
            try:
                data = json.loads(data_json)
                text = data.get("draft_reply_text")
                reply_to_id = data.get("original_mention_id")
                result = _post_text_tweet(text=text, in_reply_to_tweet_id=reply_to_id)
                self.logger.info("Posted reply for review_id %s: %s", review_id, result)
                update_human_review_status(review_id, "posted_successfully")
            except Exception as e:
                self.logger.error("Failed to post reply for review_id %s: %s", review_id, e)
                try:
                    update_human_review_status(review_id, "failed_to_post")
                except Exception as e2:
                    self.logger.error(
                        "Failed to update review status for review_id %s: %s", review_id, e2
                    )
        self.logger.info("Completed process approved replies workflow.")
