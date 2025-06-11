"""Scheduling agent to schedule orchestrator workflows."""

import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from dataclasses import dataclass

from agents import (
    Agent,  # Import Agent from SDK
    Runner,
)
from project_agents.orchestrator_agent import OrchestratorAgent
from core.cua_session_manager import CuaSessionManager

logger = logging.getLogger(__name__)

@dataclass
class AppContext:
    """Application context containing the persistent CUA session."""
    cua_session: CuaSessionManager

async def _run_cycle_with_session() -> None:
    """Run the autonomous cycle with a persistent CUA session."""
    logger.info("Starting autonomous cycle with persistent CUA session...")
    
    try:
        async with CuaSessionManager() as cua_session:
            logger.info("CUA session established, initializing orchestrator...")
            
            # Create the application context with the live session
            context = AppContext(cua_session=cua_session)
            
            # Create orchestrator agent
            orchestrator = OrchestratorAgent()
            
            # Run the orchestrator with the context containing the persistent session
            await Runner.run(
                orchestrator, 
                input="New action cycle: Assess the situation and choose a strategic action based on your goals.",
                context=context
            )
            
            logger.info("Autonomous cycle completed successfully with persistent CUA session")
    except Exception as e:
        logger.error(f"Error in autonomous cycle with CUA session: {e}", exc_info=True)


def run_autonomous_cycle_job() -> None:
    """Runs the Orchestrator's main autonomous decision-making cycle with persistent CUA session."""
    logger.info("Scheduler triggering autonomous action cycle with persistent CUA session...")
    try:
        # Run the new async function with CUA session management
        asyncio.run(_run_cycle_with_session())
    except Exception as e:
        logger.error("Error running autonomous orchestrator cycle with CUA session: %s", e)

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
                "You schedule the autonomous decision-making cycle where the OrchestratorAgent "
                "strategically decides when to check mentions, process replies, and take other actions."
            ),
            model="gpt-4.1-nano",  # Using a minimal model as it doesn't run LLM loops itself
            tools=[],  # No tools exposed by this agent itself for now
        )

        self.scheduler = scheduler
        self.logger = logging.getLogger(__name__)

    def schedule_autonomous_cycle(self, interval_minutes: int = 60) -> None:
        """Schedule the autonomous decision-making cycle at fixed intervals.

        Args:
            interval_minutes: Interval in minutes between autonomous cycles (default: 60).
        """
        try:
            job_id = "autonomous_cycle_job"
            self.scheduler.add_job(
                run_autonomous_cycle_job,
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
            self.logger.error("Failed to schedule autonomous cycle job: %s", e)
            raise
