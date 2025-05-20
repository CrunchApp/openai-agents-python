"""Scheduling agent to schedule orchestrator workflows."""

import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from agents import (
    Agent,  # Import Agent from SDK
    Runner,
)
from project_agents.orchestrator_agent import OrchestratorAgent

logger = logging.getLogger(__name__)

def run_mention_processing_job() -> None:
    """Run mention processing workflow via Runner."""
    orchestrator = OrchestratorAgent()
    try:
        asyncio.run(Runner.run(orchestrator, input="Process new X mentions."))
    except Exception as e:
        logger.error("Error running orchestrator workflow: %s", e)

def run_approved_replies_job() -> None:
    """Run approved replies processing workflow via Runner."""
    orchestrator = OrchestratorAgent()
    try:
        asyncio.run(Runner.run(orchestrator, input="Process approved X replies."))
    except Exception as e:
        logger.error("Error running orchestrator approved replies workflow: %s", e)

class SchedulingAgent(Agent):
    """Agent responsible for scheduling the OrchestratorAgent workflows."""

    def __init__(self, scheduler: BackgroundScheduler) -> None:
        """Initialize the SchedulingAgent.

        Args:
            scheduler: The BackgroundScheduler instance to use.
        """  # Call super().__init__ with SDK configuration
        super().__init__(
            name="Scheduling Agent",
            instructions=(
                "You are an agent responsible for managing scheduled tasks for the X Agentic Unit. "
                "You can schedule workflows like mention processing."
            ),
            model="gpt-4.1-nano",  # Using a minimal model as it doesn't run LLM loops itself
            tools=[],  # No tools exposed by this agent itself for now
        )

        self.scheduler = scheduler
        self.logger = logging.getLogger(__name__)

    def schedule_mention_processing(self, interval_minutes: int = 5) -> None:
        """Schedule the process_new_mentions_workflow at fixed intervals.

        Args:
            interval_minutes: Interval in minutes between job runs.
        """

        try:
            job_id = "process_mentions_job"
            self.scheduler.add_job(
                run_mention_processing_job,
                trigger="interval",
                minutes=interval_minutes,
                id=job_id,
                replace_existing=True,
            )
            self.logger.info(
                "Scheduled job '%s' to run every %d minutes.",
                job_id,
                interval_minutes,
            )
        except Exception as e:
            self.logger.error("Failed to schedule job: %s", e)
            raise

    def schedule_approved_reply_processing(self, interval_minutes: int = 1) -> None:
        """Schedule the process_approved_replies_workflow at fixed intervals."""

        try:
            job_id = "process_approved_replies_job"
            self.scheduler.add_job(
                run_approved_replies_job,
                trigger="interval",
                minutes=interval_minutes,
                id=job_id,
                replace_existing=True,
            )
            self.logger.info(
                "Scheduled job '%s' to run every %d minutes.",
                job_id,
                interval_minutes,
            )
        except Exception as e:
            self.logger.error("Failed to schedule approved replies job: %s", e)
            raise
