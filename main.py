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
    """Test the CUA latest tweet reading functionality via OrchestratorAgent."""
    logger = logging.getLogger(__name__)
    
    logger.info("Starting X Agentic Unit - CUA Latest Tweet Reading Test")
    logger.info("Testing CUA capability to read latest tweet from own profile")
    
    # Check CUA configuration
    if settings.x_cua_user_data_dir:
        logger.info("Using persistent browser session from: %s", settings.x_cua_user_data_dir)
        logger.info("Ensure you have completed authentication setup using scripts/setup_cua_authentication.py")
    else:
        logger.warning("X_CUA_USER_DATA_DIR not set - using fresh browser session")
        logger.warning("For authenticated profile access, set X_CUA_USER_DATA_DIR in .env and run authentication setup")
    
    try:
        # Initialize the OrchestratorAgent
        logger.info("Initializing OrchestratorAgent...")
        orchestrator = OrchestratorAgent()
        
        logger.info("Starting CUA latest tweet reading workflow...")
        logger.info("The CUA will navigate to profile and extract the latest tweet text")
        
        # Call the CUA latest tweet reading method
        result_message = orchestrator.get_latest_own_tweet_text_via_cua()
        
        # Log the result
        logger.info("CUA Latest Tweet Reading Result: %s", result_message)
        
        # Provide user guidance based on result format
        if "SUCCESS" in result_message and "Extracted latest tweet text:" in result_message:
            # Extract just the tweet text from the success message
            try:
                # Find the tweet text between quotes
                start_quote = result_message.find('"') + 1
                end_quote = result_message.rfind('"')
                if start_quote > 0 and end_quote > start_quote:
                    extracted_text = result_message[start_quote:end_quote]
                    logger.info("[SUCCESS] Latest tweet text successfully extracted!")
                    logger.info("[EXTRACTED TEXT] %s", extracted_text)
                    logger.info("[CHARACTER COUNT] %d characters", len(extracted_text))
                else:
                    logger.info("[SUCCESS] Tweet text extracted, but could not parse quotes")
            except Exception as e:
                logger.warning("Could not parse extracted text from success message: %s", e)
            
            logger.info("[NEXT STEPS] Verify this matches the actual latest tweet on your X profile")
            
        elif "SUCCESS" in result_message:
            logger.info("[SUCCESS] Tweet reading operation completed successfully!")
            logger.info("[NEXT STEPS] Check the result message above for extracted content")
            
        elif "COMPLETED" in result_message:
            logger.info("[PARTIAL SUCCESS] CUA workflow completed but may not have extracted text")
            logger.info("[TIP] Check if the workflow reached profile page and identified tweets")
            
        elif "SESSION_INVALIDATED" in result_message:
            logger.warning("[SESSION ISSUE] Browser session is no longer authenticated")
            logger.info("[TIP] Run authentication setup: python scripts/setup_cua_authentication.py")
            
        elif "FAILED" in result_message:
            logger.warning("[FAILED] Tweet reading failed. Check the result message above")
            if "Could not navigate to profile page" in result_message:
                logger.info("[TIP] Check if you're on X.com and authenticated")
            elif "no tweets were found" in result_message.lower():
                logger.info("[TIP] Your profile may be empty or tweets are not visible")
            elif "could not reliably extract" in result_message.lower():
                logger.info("[TIP] The UI structure may have changed or tweet text was in an image")
            
            logger.info("[TIP] If authentication issues occurred, run: python scripts/setup_cua_authentication.py")
            
        else:
            logger.warning("[UNKNOWN] Unexpected result format. Check the result message above")
            logger.info("[TIP] If session issues occurred, run: python scripts/setup_cua_authentication.py")
        
        # Additional debugging info
        logger.info("=== DEBUGGING INFO ===")
        logger.info("CUA latest tweet reading features:")
        logger.info("  - Profile navigation using 'g+p' keyboard shortcut")
        logger.info("  - Tweet timeline identification and parsing")
        logger.info("  - Text extraction from latest tweet element")
        logger.info("  - Session invalidation detection")
        logger.info("  - Autonomous cookie banner handling")
        logger.info("  - Comprehensive error reporting")
        
    except Exception as e:
        logger.error("CUA latest tweet reading test failed: %s", e, exc_info=True)
        logger.error("[FAILED] Test failed. Check your configuration and authentication setup")
    
    logger.info("CUA Latest Tweet Reading Test completed.")


if __name__ == "__main__":
    main()
