"""Scheduling agent to schedule orchestrator workflows."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from agents.orchestrator_agent import OrchestratorAgent
from agents import Agent # Import Agent from SDK

class SchedulingAgent(Agent):
    """Agent responsible for scheduling the OrchestratorAgent workflows."""

    def __init__(self, orchestrator: OrchestratorAgent, scheduler: BackgroundScheduler) -> None:
        """Initialize the SchedulingAgent.

        Args:
            orchestrator: The OrchestratorAgent instance to schedule.
            scheduler: The BackgroundScheduler instance to use.
        """ # Call super().__init__ with SDK configuration
        super().__init__(
            name="Scheduling Agent",
            instructions=(
                "You are an agent responsible for managing scheduled tasks for the X Agentic Unit. "
                "You can schedule workflows like mention processing."
            ),
            model="gpt-4.1-nano", # Using a minimal model as it doesn't run LLM loops itself
            tools=[] # No tools exposed by this agent itself for now
        )

        # Keep existing initialization for direct call pattern in main.py
        self.orchestrator = orchestrator
        self.scheduler = scheduler
        self.logger = logging.getLogger(__name__)

    def schedule_mention_processing(self, interval_minutes: int = 5) -> None:
        """Schedule the process_new_mentions_workflow at fixed intervals.

        Args:
            interval_minutes: Interval in minutes between job runs.
        """
        try:
            job_id = "process_mentions_job"
            # Access scheduler and orchestrator from instance variables
            self.scheduler.add_job(
                self.orchestrator.process_new_mentions_workflow,
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