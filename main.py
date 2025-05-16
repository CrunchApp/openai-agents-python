"""Main entry point for the X Agentic Unit application."""

from core.config import settings



import logging
import time

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

from agents.orchestrator_agent import OrchestratorAgent
from core.scheduler_setup import initialize_scheduler
from agents.scheduling_agent import SchedulingAgent


def main() -> None:
    """Run the orchestrator agent workflow via scheduler."""
    logger = logging.getLogger(__name__)
    orchestrator = OrchestratorAgent()

    try:
        scheduler = initialize_scheduler()
        scheduling_agent = SchedulingAgent(orchestrator, scheduler)
        scheduling_agent.schedule_mention_processing()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown signal received. Shutting down scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler shut down. Exiting.")
    except Exception as e:
        logger.error("An error occurred during workflow execution: %s", e)


if __name__ == "__main__":
    main() 