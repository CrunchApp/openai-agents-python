"""Main entry point for the X Agentic Unit application."""

import logging
from datetime import datetime, timezone

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

from project_agents.orchestrator_agent import OrchestratorAgent  # noqa: E402


def main() -> None:
    """Test the CUA tweet posting functionality via OrchestratorAgent."""
    logger = logging.getLogger(__name__)
    
    logger.info("Starting X Agentic Unit - Enhanced CUA Tweet Posting Test")
    logger.info("Testing improved browser configuration and interaction handling")
    
    # Check CUA configuration
    if settings.x_cua_user_data_dir:
        logger.info("Using persistent browser session from: %s", settings.x_cua_user_data_dir)
        logger.info("Ensure you have completed authentication setup using scripts/setup_cua_authentication.py")
    else:
        logger.warning("X_CUA_USER_DATA_DIR not set - using fresh browser session")
        logger.warning("For authenticated posting, set X_CUA_USER_DATA_DIR in .env and run authentication setup")
    
    try:
        # Initialize the OrchestratorAgent
        logger.info("Initializing OrchestratorAgent...")
        orchestrator = OrchestratorAgent()
        
        # Define sample tweet text - shorter for easier testing
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        sample_tweet_text = f"Enhanced CUA test #{timestamp[-8:]} - improved browser automation! #XAgent #AI"
        
        logger.info("Sample tweet text: %s", sample_tweet_text)
        logger.info("Character count: %d", len(sample_tweet_text))
        logger.info("Starting enhanced CUA tweet posting workflow...")
        
        # Call the CUA tweet posting method
        result_message = orchestrator.post_tweet_via_cua(tweet_text=sample_tweet_text)
        
        # Log the result
        logger.info("Enhanced CUA Tweet Posting Result: %s", result_message)
        
        # Provide user guidance based on improved result format
        if "SUCCESS" in result_message:
            logger.info("[SUCCESS] Tweet posting successful! Check your X account to verify.")
            logger.info("[NEXT STEPS] The enhanced CUA configuration is working properly.")
        elif "COMPLETED" in result_message:
            logger.info("[PARTIAL SUCCESS] Operation completed but connection closed. Check X.com manually to verify if tweet was posted.")
            logger.info("[TIP] This may indicate the tweet was posted but verification wasn't captured.")
        elif "SESSION_INVALIDATED" in result_message:
            logger.warning("[SESSION ISSUE] Browser session is no longer authenticated.")
            logger.info("[TIP] Run authentication setup: python scripts/setup_cua_authentication.py")
        elif "FAILED" in result_message:
            logger.warning("[FAILED] Tweet posting failed. Check the result message above.")
            if "timed out" in result_message.lower():
                logger.info("[TIP] The operation timed out. This may indicate network issues or complex UI interactions.")
            elif "non-functional" in result_message.lower():
                logger.info("[TIP] Post button interaction issue. Our enhanced configuration should help with this.")
            logger.info("[TIP] If authentication issues occurred, run: python scripts/setup_cua_authentication.py")
        else:
            logger.warning("[UNKNOWN] Unexpected result format. Check the result message above.")
            logger.info("[TIP] If session issues occurred, run: python scripts/setup_cua_authentication.py")
        
        # Additional debugging info
        logger.info("=== DEBUGGING INFO ===")
        logger.info("Enhanced browser features enabled:")
        logger.info("  - Anti-automation detection measures")
        logger.info("  - Improved click timing and interaction")
        logger.info("  - Better JavaScript execution handling")
        logger.info("  - Enhanced page stabilization")
        logger.info("  - Detailed CUA prompt guidance")
        
    except Exception as e:
        logger.error("Enhanced CUA tweet posting test failed: %s", e, exc_info=True)
        logger.error("[FAILED] Test failed. Check your configuration and authentication setup.")
    
    logger.info("Enhanced CUA Tweet Posting Test completed.")


if __name__ == "__main__":
    main()
