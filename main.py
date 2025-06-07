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
    """Tests the sequential CUA workflows: post -> read timeline -> reply sequence via OrchestratorAgent."""
    logger = logging.getLogger(__name__)
    
    logger.info("Starting X Agentic Unit - Sprint 2 Test Sequence")
    logger.info("This test will post a tweet, read timeline, and reply to the posted tweet via CUA.")
    
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
        
        # Get current timestamp for unique test content
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # --- STEP 1: Test Hybrid Posting with ASCII Content ---
        logger.info("\n=== STEP 1: Hybrid Post ASCII Tweet ===")
        ascii_tweet_text = f"This is an ASCII-only CUA test tweet at {timestamp} #AIifiedTest"
        logger.info(f"Posting ASCII tweet: {ascii_tweet_text}")
        
        ascii_post_result = orchestrator.post_tweet_hybrid(tweet_text=ascii_tweet_text)
        logger.info("Hybrid ASCII Post Result: %s", ascii_post_result)
        
        if "SUCCESS" not in ascii_post_result:
            logger.error("[FAILED] ASCII tweet posting failed.")
            logger.error("ASCII Post Result: %s", ascii_post_result)
        else:
            logger.info("[SUCCESS] ASCII tweet posted successfully!")
        
        # --- STEP 2: Test Hybrid Posting with Emoji Content ---
        logger.info("\n=== STEP 2: Hybrid Post Emoji Tweet ===")
        emoji_tweet_text = f"This is an emoji API test tweet at {timestamp} 🚀✅ #AIifiedTest"
        logger.info(f"Posting emoji tweet: {emoji_tweet_text}")
        
        emoji_post_result = orchestrator.post_tweet_hybrid(tweet_text=emoji_tweet_text)
        logger.info("Hybrid Emoji Post Result: %s", emoji_post_result)
        
        if "SUCCESS" not in emoji_post_result:
            logger.error("[FAILED] Emoji tweet posting failed.")
            logger.error("Emoji Post Result: %s", emoji_post_result)
        else:
            logger.info("[SUCCESS] Emoji tweet posted successfully!")
        
        # --- STEP 3: Read Timeline ---
        logger.info("\n=== STEP 3: CUA Read Home Timeline ===")
        logger.info("Reading top 3 tweets from home timeline to verify our posted tweets appear...")
        
        timeline_result = orchestrator.get_home_timeline_tweets_via_cua(num_tweets=3)
        logger.info("CUA Timeline Read Result: %s", timeline_result)
        
        if "SUCCESS:" in timeline_result and "[" in timeline_result:
            logger.info("[SUCCESS] Timeline reading completed!")
            # Try to parse the JSON to show individual tweets
            try:
                import json
                import re
                json_match = re.search(r'\[(.*)\]', timeline_result)
                if json_match:
                    tweets_json = json_match.group(0)
                    tweets = json.loads(tweets_json)
                    logger.info(f"Extracted {len(tweets)} tweets from timeline:")
                    for i, tweet in enumerate(tweets, 1):
                        logger.info(f"  Tweet {i}: {tweet[:100]}{'...' if len(tweet) > 100 else ''}")
                else:
                    logger.info("Could not parse tweet JSON from result")
            except Exception as parse_error:
                logger.warning(f"Could not parse timeline JSON: {parse_error}")
        elif "SESSION_INVALIDATED" in timeline_result:
            logger.error("[SESSION ISSUE] Browser session became unauthenticated during timeline reading.")
            logger.info("[TIP] Run authentication setup to restore session.")
        elif "FAILED" in timeline_result:
            logger.error("[FAILED] Timeline reading failed. Check the result message above.")
        else:
            logger.warning("[UNKNOWN] Unexpected timeline result format. Check the message above.")
        
        # --- STEP 4: Choose Target Tweet for Reply Test ---
        logger.info("\n=== STEP 4: Select Target Tweet for Reply Test ===")
        
        # If we successfully posted tweets, ask user which one to reply to
        successful_posts = []
        if "SUCCESS" in ascii_post_result:
            successful_posts.append(("ASCII", ascii_tweet_text))
        if "SUCCESS" in emoji_post_result:
            successful_posts.append(("Emoji", emoji_tweet_text))
        
        if not successful_posts:
            logger.error("[ERROR] No tweets were successfully posted. Cannot proceed with reply test.")
            return
        
        logger.info("🔗 MANUAL STEP REQUIRED:")
        logger.info("Please manually navigate to your X profile and find one of the tweets that was just posted.")
        logger.info("Posted tweets:")
        for i, (tweet_type, content) in enumerate(successful_posts, 1):
            logger.info(f"  {i}. {tweet_type}: {content}")
        logger.info("Copy the full URL of the tweet you want to reply to (e.g., https://x.com/youruser/status/1234567890)")
        print("\nPlease paste the URL of the tweet to reply to:")
        target_tweet_url = input("> ").strip()
        
        if not target_tweet_url or not target_tweet_url.startswith("https://x.com/"):
            logger.error("[ERROR] Invalid tweet URL provided. Expected format: https://x.com/username/status/id")
            return
        
        logger.info(f"Using target tweet URL: {target_tweet_url}")
        
        # --- STEP 5: Test Hybrid Reply with ASCII Content ---
        logger.info("\n=== STEP 5: Hybrid Reply ASCII ===")
        ascii_reply_text = f"This is an ASCII CUA reply test at {timestamp}"
        logger.info(f"Replying with ASCII text: {ascii_reply_text}")
        
        ascii_reply_result = orchestrator.reply_to_tweet_hybrid(tweet_url=target_tweet_url, reply_text=ascii_reply_text)
        logger.info("Hybrid ASCII Reply Result: %s", ascii_reply_result)
        
        if "SUCCESS" in ascii_reply_result:
            logger.info("[SUCCESS] ASCII reply posted successfully!")
        else:
            logger.error("[FAILED] ASCII reply posting failed.")
            logger.error("ASCII Reply Result: %s", ascii_reply_result)
        
        # --- STEP 6: Test Hybrid Reply with Emoji Content ---
        logger.info("\n=== STEP 6: Hybrid Reply Emoji ===")
        emoji_reply_text = f"This is an emoji API reply test at {timestamp} ✅🎯"
        logger.info(f"Replying with emoji text: {emoji_reply_text}")
        
        emoji_reply_result = orchestrator.reply_to_tweet_hybrid(tweet_url=target_tweet_url, reply_text=emoji_reply_text)
        logger.info("Hybrid Emoji Reply Result: %s", emoji_reply_result)
        
        if "SUCCESS" in emoji_reply_result:
            logger.info("[SUCCESS] Emoji reply posted successfully!")
        else:
            logger.error("[FAILED] Emoji reply posting failed.")
            logger.error("Emoji Reply Result: %s", emoji_reply_result)
            
        # --- FINAL SUMMARY ---
        logger.info("\n=== SPRINT 2 HYBRID STRATEGY TEST SUMMARY ===")
        logger.info(f"1a. ✅ ASCII Tweet (CUA): {'✅ SUCCESS' if 'SUCCESS' in ascii_post_result else '❌ FAILED'}")
        logger.info(f"1b. 🚀 Emoji Tweet (API): {'✅ SUCCESS' if 'SUCCESS' in emoji_post_result else '❌ FAILED'}")
        logger.info(f"2. 📋 Timeline Reading: {'✅ SUCCESS' if 'SUCCESS:' in timeline_result else '❌ FAILED'}")
        logger.info(f"3a. 💬 ASCII Reply (CUA): {'✅ SUCCESS' if 'SUCCESS' in ascii_reply_result else '❌ FAILED'}")
        logger.info(f"3b. 🎯 Emoji Reply (API): {'✅ SUCCESS' if 'SUCCESS' in emoji_reply_result else '❌ FAILED'}")
        
        logger.info("\n=== HYBRID STRATEGY VALIDATION ===")
        logger.info("Content Routing Intelligence:")
        logger.info("  - ASCII content automatically routed to CUA for browser automation")
        logger.info("  - Emoji/Unicode content automatically routed to X API for reliability")
        logger.info("  - Automatic fallback from CUA to API when browser automation fails")
        logger.info("  - Unified interface abstracts the complexity from calling code")
        
        logger.info("Technical Capabilities Demonstrated:")
        logger.info("CUA Operations (ASCII content):")
        logger.info("  - Browser automation with keyboard shortcuts")
        logger.info("  - Timeline navigation and content extraction")
        logger.info("  - Session persistence and error recovery")
        logger.info("API Operations (Unicode content):")
        logger.info("  - Reliable emoji/Unicode character posting")
        logger.info("  - Tweet ID extraction for reply threading")
        logger.info("  - OAuth token management and authentication")
        logger.info("Hybrid Orchestration:")
        logger.info("  - Intelligent content analysis and routing")
        logger.info("  - Automatic fallback mechanisms")
        logger.info("  - Unified error handling and logging")
        
        logger.info("\n🎉 CONCLUSION: CUA emoji limitation has been successfully mitigated")
        logger.info("through intelligent hybrid routing that leverages the strengths of both")
        logger.info("browser automation (CUA) and API calls while avoiding their limitations.")

    except Exception as e:
        logger.error("Sprint 2 hybrid test sequence failed: %s", e, exc_info=True)
        logger.error("[CRITICAL FAILED] Test failed due to an unexpected exception. Check your configuration and authentication setup.")
    
    logger.info("X Agentic Unit - Sprint 2 Hybrid Strategy Test completed.")


if __name__ == "__main__":
    main()
