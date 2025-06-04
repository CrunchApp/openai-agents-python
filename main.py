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
        # CUA test
        logger.info("Starting CUA Test...")
        async with LocalPlaywrightComputer() as computer:
            cua_agent = ComputerUseAgent(computer=computer)
            try:
                result = await Runner.run(
                    cua_agent,
                    input="Navigate to x.com and take a screenshot of the main page."
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
