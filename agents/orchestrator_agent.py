"""Orchestrator agent module for managing workflows."""

import logging

from .x_interaction_agent import XInteractionAgent


class OrchestratorAgent:
    """Central coordinator agent for managing X platform interactions."""

    def __init__(self) -> None:
        """Initialize the OrchestratorAgent with a logger."""
        self._logger = logging.getLogger(__name__)

    def run_simple_post_workflow(self, content: str) -> None:
        """Run a simple workflow that posts content to X.

        Args:
            content: The text content to post as a tweet.
        """
        self._logger.info("Starting simple post workflow.")
        x_agent = XInteractionAgent()
        try:
            result = x_agent.post_tweet(text_to_post=content)
            self._logger.info(
                "Workflow completed successfully with result: %s", result
            )
        except Exception as e:
            self._logger.error("Workflow failed: %s", e)
            raise 