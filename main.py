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

from core.computer_env.local_playwright_computer import LocalPlaywrightComputer  # noqa: E402
from project_agents.computer_use_agent import ComputerUseAgent  # noqa: E402
from agents import Runner  # noqa: E402


async def main() -> None:
    """Run the orchestrator agent workflow via scheduler and Runner."""
    logger = logging.getLogger(__name__)

    try:
        # CUA test with optional persistent session
        logger.info("Starting CUA Test...")
        if settings.x_cua_user_data_dir:
            logger.info("Using persistent browser session from: %s", settings.x_cua_user_data_dir)
        else:
            logger.info("Using fresh browser session (no persistent data directory)")
        
        async with LocalPlaywrightComputer(user_data_dir_path=settings.x_cua_user_data_dir) as computer:
            cua_agent = ComputerUseAgent(computer=computer)
            try:
                # Test task that typically requires authentication
                test_task = (
                    "Navigate to the X.com notifications page and take a screenshot. "
                    "If you encounter a login screen instead of notifications, "
                    "note this in your response as it indicates an unauthenticated session."
                )
                result = await Runner.run(
                    cua_agent,
                    input=test_task
                )
                logger.info("CUA Task Result (Final Output): %s", result.final_output)
            except Exception as e:
                logger.error("CUA Task failed: %s", e, exc_info=True)
        logger.info("CUA Test Finished.")
    except KeyboardInterrupt:
        logger.info("Shutdown signal received. Exiting CUA test.")
    except Exception as e:
        logger.error("An error occurred during workflow execution: %s", e)


if __name__ == "__main__":
    asyncio.run(main())
