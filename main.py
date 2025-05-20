"""Main entry point for the X Agentic Unit application."""

import asyncio
import logging
import time

from core.config import settings

# Configure logging before importing application modules
log_level = settings.log_level.upper()
logging.basicConfig(
    level=log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(filename="data/app.log"),
    ],
)

from core.scheduler_setup import initialize_scheduler  # noqa: E402
from project_agents.scheduling_agent import SchedulingAgent  # noqa: E402


async def main() -> None:
    """Run the orchestrator agent workflow via scheduler and Runner."""
    logger = logging.getLogger(__name__)

    try:
        # Initialize scheduler and schedule the orchestrator workflow
        scheduler = initialize_scheduler()
        scheduling_agent = SchedulingAgent(scheduler)
        scheduling_agent.schedule_mention_processing()
        scheduling_agent.schedule_approved_reply_processing()
        # Keep the application running to allow scheduled jobs to execute
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown signal received. Shutting down scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler shut down. Exiting.")
    except Exception as e:
        logger.error("An error occurred during workflow execution: %s", e)


if __name__ == "__main__":
    asyncio.run(main())
