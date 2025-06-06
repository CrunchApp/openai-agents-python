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
    """Tests the sequential CUA read and post workflows via OrchestratorAgent."""
    logger = logging.getLogger(__name__)
    
    logger.info("Starting X Agentic Unit - Sequential CUA Read & Post Test")
    logger.info("This test will first read the latest tweet, then attempt to post a new one.")
    
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
        
        # --- STEP 1: Read Latest Tweet ---
        logger.info("\n=== STEP 1: CUA Read Latest Own Tweet ===")
        logger.info("Attempting to read the latest tweet text from own profile...")
        
        read_result_message = orchestrator.get_latest_own_tweet_text_via_cua()
        
        logger.info("CUA Latest Tweet Reading Result: %s", read_result_message)
        
        can_proceed_to_post = True
        
        if "SUCCESS" in read_result_message and "Extracted latest tweet text:" in read_result_message:
            try:
                start_quote = read_result_message.find('"') + 1
                end_quote = read_result_message.rfind('"')
                if start_quote > 0 and end_quote > start_quote:
                    extracted_text = read_result_message[start_quote:end_quote]
                    logger.info("[SUCCESS] Latest tweet text successfully extracted!")
                    logger.info("[EXTRACTED TEXT] %s", extracted_text)
                    logger.info("[CHARACTER COUNT] %d characters", len(extracted_text))
                else:
                    logger.info("[SUCCESS] Tweet text extracted, but could not parse quotes")
            except Exception as e:
                logger.warning("Could not parse extracted text from success message: %s", e)
            logger.info("[NEXT STEPS] Verify this matches the actual latest tweet on your X profile.")
            
        elif "SUCCESS" in read_result_message:
            logger.info("[SUCCESS] Tweet reading operation completed successfully!")
            logger.info("[NEXT STEPS] Check the result message above for extracted content.")
            
        elif "COMPLETED" in read_result_message:
            logger.info("[PARTIAL SUCCESS] CUA workflow completed but may not have extracted text.")
            logger.info("[TIP] Check if the workflow reached profile page and identified tweets.")
            
        elif "SESSION_INVALIDATED" in read_result_message:
            logger.error("[SESSION ISSUE] Browser session is no longer authenticated. Aborting post test.")
            logger.info("[TIP] Run authentication setup: python scripts/setup_cua_authentication.py")
            can_proceed_to_post = False
            
        elif "FAILED" in read_result_message:
            logger.error("[FAILED] Tweet reading failed. Aborting post test.")
            if "Could not navigate to profile page" in read_result_message:
                logger.info("[TIP] Check if you're on X.com and authenticated.")
            elif "no tweets were found" in read_result_message.lower():
                logger.info("[TIP] Your profile may be empty or tweets are not visible.")
            elif "could not reliably extract" in read_result_message.lower():
                logger.info("[TIP] The UI structure may have changed or tweet text was in an image.")
            logger.info("[TIP] If authentication issues occurred, run: python scripts/setup_cua_authentication.py")
            can_proceed_to_post = False
            
        else:
            logger.warning("[UNKNOWN] Unexpected read result format. Check the message above.")
            logger.info("[TIP] If session issues occurred, run: python scripts/setup_cua_authentication.py")
            # Decide if an unknown result should stop the post - generally safer to stop
            can_proceed_to_post = False

        # --- STEP 2: Post a New Tweet (if read was successful or didn't invalidate session) ---
        if can_proceed_to_post:
            logger.info("\n=== STEP 2: CUA Post New Tweet ===")
            logger.info("Attempting to post a new tweet after successful read (or non-fatal issue)...")
            
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            post_tweet_text = f"Sequential CUA Test: Read completed! Now posting this. {timestamp} #XAgent #SequentialTest"
            
            post_result_message = orchestrator.post_tweet_via_cua(tweet_text=post_tweet_text)
            
            logger.info("CUA Tweet Posting Result: %s", post_result_message)
            
            if "SUCCESS" in post_result_message:
                logger.info("[SUCCESS] New tweet successfully posted!")
                logger.info("[NEXT STEPS] Verify this tweet appears on your X profile.")
            elif "SESSION_INVALIDATED" in post_result_message:
                logger.error("[SESSION ISSUE] Browser session became unauthenticated during post attempt.")
                logger.info("[TIP] This indicates a session stability problem. Run authentication setup.")
            elif "FAILED" in post_result_message:
                logger.error("[FAILED] Tweet posting failed. Check the result message above.")
                logger.info("[TIP] Review logs for CUA actions leading to failure. Authentication might be an issue.")
            else:
                logger.warning("[UNKNOWN] Unexpected post result format. Check the message above.")
        else:
            logger.info("\nSkipping tweet posting due to previous CUA read failure or session invalidation.")
        
        logger.info("\n=== DEBUGGING INFO ===")
        logger.info("CUA latest tweet reading features:")
        logger.info("  - Profile navigation using 'g+p' keyboard shortcut")
        logger.info("  - Tweet timeline identification and parsing")
        logger.info("  - Text extraction from latest tweet element")
        logger.info("  - Session invalidation detection")
        logger.info("  - Autonomous cookie banner handling")
        logger.info("  - Comprehensive error reporting")
        logger.info("CUA tweet posting features:")
        logger.info("  - Compose area opening via 'n' keyboard shortcut")
        logger.info("  - Tweet text input via typing action")
        logger.info("  - Tweet posting via 'Ctrl+Shift+Enter' keyboard shortcut")
        logger.info("  - Session invalidation detection")
        logger.info("  - Autonomous cookie banner handling")
        logger.info("  - Comprehensive error reporting")
            
    except Exception as e:
        logger.error("Sequential CUA Read & Post test failed: %s", e, exc_info=True)
        logger.error("[CRITICAL FAILED] Test failed due to an unexpected exception. Check your configuration and authentication setup.")
    
    logger.info("X Agentic Unit - Sequential CUA Read & Post Test completed.")


if __name__ == "__main__":
    main()
