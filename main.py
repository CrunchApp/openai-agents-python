"""Main entry point for the X Agentic Unit application."""

from core.config import settings

print("--- SETTINGS OBJECT ---")
print(f"Loaded X_API_KEY: {settings.x_api_key}")
print(f"Loaded X_API_SECRET_KEY: {settings.x_api_secret_key}") # Check this value
print(f"Loaded TOKEN_ENCRYPTION_KEY: {settings.token_encryption_key}") # Check this value
print("--- END SETTINGS OBJECT ---")

import logging

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


def main() -> None:
    """Run the orchestrator agent workflow."""
    logger = logging.getLogger(__name__)
    orchestrator = OrchestratorAgent()
    try:
        orchestrator.run_simple_post_workflow(
            "Hello from the X Agentic Unit! This is a test tweet via the MVP."
        )
    except Exception as e:
        logger.error("An error occurred during workflow execution: %s", e)


if __name__ == "__main__":
    main() 