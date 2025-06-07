"""Main entry point for the X Agentic Unit application."""

import logging
from datetime import datetime, timezone

from core.config import settings
from project_agents.orchestrator_agent import OrchestratorAgent
from project_agents.content_creation_agent import ContentCreationAgent
from project_agents.research_agent import ResearchAgent

# Configure logging before importing application modules
log_level = settings.log_level.upper()

# Configure logging with UTF-8 encoding to handle Unicode characters (like emojis)
import sys
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setStream(sys.stdout)
# Ensure UTF-8 encoding for console output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        console_handler,
        logging.FileHandler(filename="data/app.log", encoding='utf-8'),
    ],
)


def main() -> None:
    """Tests the sequential CUA read and post workflows via OrchestratorAgent."""
    logger = logging.getLogger(__name__)
    
    logger.info("Starting X Agentic Unit - Sprint 1 Test Sequence")
    logger.info("This test will perform research, draft an original post, and attempt to like a tweet via CUA.")
    
    # Check CUA configuration
    if settings.x_cua_user_data_dir:
        logger.info("Using persistent browser session from: %s", settings.x_cua_user_data_dir)
        logger.info("Ensure you have completed authentication setup using scripts/setup_cua_authentication.py")
    else:
        logger.warning("X_CUA_USER_DATA_DIR not set - using fresh browser session")
        logger.warning("For authenticated profile access, set X_CUA_USER_DATA_DIR in .env and run authentication setup")
    
    try:
        # Initialize the OrchestratorAgent and ContentCreationAgent
        logger.info("Initializing OrchestratorAgent and ContentCreationAgent...")
        orchestrator = OrchestratorAgent()
        content_creation_agent = ContentCreationAgent()
        
        # --- STEP 1: Research Topic ---
        logger.info("\n=== STEP 1: Researching Topic ===")
        research_query = "latest news on GPT-5 capabilities"
        logger.info(f"Calling ResearchAgent for query: '{research_query}'")
        research_result = orchestrator.research_topic_for_aiified(research_query)
        logger.info("Research Result: %s", research_result)

        # --- STEP 2: Draft Original Post (Simulate HIL) ---
        logger.info("\n=== STEP 2: Drafting Original Post ===")
        if "FAILED" not in research_result:
            persona_prompt = ("You are 'AIified', an X account focused on sharing insightful news, "
                              "developments, and engaging with people in the fields of Large Language Models (LLMs), "
                              "Machine Learning (ML), and Artificial Intelligence (AI). Keep tweets engaging and professional.")
            
            logger.info("Calling ContentCreationAgent to draft original post...")
            draft_data = content_creation_agent.draft_original_post(topic_summary=research_result, persona_prompt=persona_prompt)
            
            logger.info("Drafted Post Data: %s", draft_data)
            if "draft_tweet_text" in draft_data:
                logger.info("Human, please review draft: \n%s", draft_data["draft_tweet_text"])
                logger.info("\n[SIMULATED HIL] Assuming draft is approved for next steps.\n")
            else:
                logger.error("Drafting step failed or returned unexpected data.")
        else:
            logger.warning("Skipping drafting step due to failed research result.")
            
        # --- STEP 3: Like a Tweet via CUA ---
        logger.info("\n=== STEP 3: CUA Like a Tweet ===")
        # IMPORTANT: Replace with a real tweet URL you want the AIified account to like
        test_tweet_url = "https://x.com/aghashalokh/status/1895573588910239803" # Placeholder
        logger.info(f"Attempting to like tweet at URL: {test_tweet_url}")
        
        like_result = orchestrator.like_tweet_via_cua(tweet_url=test_tweet_url)
        
        logger.info("CUA Like Tweet Result: %s", like_result)
        
        if "SUCCESS" in like_result:
            logger.info("[SUCCESS] Tweet successfully liked!")
            logger.info("[NEXT STEPS] Manually verify if the target tweet was liked by your X test account.")
        elif "SESSION_INVALIDATED" in like_result:
            logger.error("[SESSION ISSUE] Browser session became unauthenticated during like attempt.")
            logger.info("[TIP] This indicates a session stability problem. Run authentication setup.")
        elif "FAILED" in like_result:
            logger.error("[FAILED] Liking tweet failed. Check the result message above.")
            logger.info("[TIP] Review logs for CUA actions leading to failure. Authentication might be an issue.")
        else:
            logger.warning("[UNKNOWN] Unexpected like result format. Check the message above.")
            
        logger.info("\n=== DEBUGGING INFO ===")
        logger.info("CUA tweet liking features:")
        logger.info("  - Direct navigation to tweet URL")
        logger.info("  - Tweet identification and 'l' keyboard shortcut for liking")
        logger.info("  - Session invalidation detection")
        logger.info("  - Autonomous cookie banner handling")
        logger.info("  - Comprehensive error reporting")
        logger.info("Research Agent features:")
        logger.info("  - Web search for AI/ML topics")
        logger.info("  - Concise summarization of findings")
        logger.info("Content Creation Agent features:")
        logger.info("  - Drafting original posts based on topic and persona")
        logger.info("  - Integration with HIL for review")

    except Exception as e:
        logger.error("Sprint 1 test sequence failed: %s", e, exc_info=True)
        logger.error("[CRITICAL FAILED] Test failed due to an unexpected exception. Check your configuration and authentication setup.")
    
    logger.info("X Agentic Unit - Sprint 1 Test Sequence completed.")


if __name__ == "__main__":
    main()
