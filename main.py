"""Main entry point for the X Agentic Unit application."""

import logging
import json
import re
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
    """Tests the three new CUA methods: repost, follow, and search functionality."""
    logger = logging.getLogger(__name__)
    
    logger.info("Starting X Agentic Unit - New CUA Methods Testing (Task 8.1)")
    logger.info("🔧 Testing the three newly implemented CUA methods: repost, follow, and search.")
    
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
        
        # Get current timestamp for test logging
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        logger.info(f"\n🚀 NEW CUA METHODS TESTING - {timestamp}")
        logger.info("=" * 70)
        logger.info("Task 8.1: Testing repost_tweet_via_cua, follow_user_via_cua, search_x_for_topic_via_cua")
        logger.info("Expected Results: All three methods should work with proper CUA integration")
        logger.info("=" * 70)
        
        # Test data - hardcoded URLs and queries for testing
        test_repost_url = "https://x.com/aghashalokh/status/1929536138949144653"  # Example OpenAI tweet
        test_profile_url = "https://x.com/OpenAI"  # OpenAI's profile for following
        test_search_query = "OpenAI Sora"  # Topical AI search query
        
        # Track all test results
        all_results = []
        
        # =================================================================
        # TEST 1: REPOST TWEET VIA CUA
        # =================================================================
        logger.info("\n" + "=" * 50)
        logger.info("🔄 TEST 1: REPOST TWEET VIA CUA")
        logger.info("=" * 50)
        logger.info(f"Test URL: {test_repost_url}")
        logger.info("Expected: Navigate to tweet page, press 't', click 'Repost' option")
        logger.info("Success criteria: Tweet reposted successfully or proper error handling")
        
        try:
            logger.info("Executing repost_tweet_via_cua...")
            repost_result = orchestrator.repost_tweet_via_cua(test_repost_url)
            logger.info(f"Repost CUA Result: {repost_result}")
            
            # Analyze result
            if "SUCCESS:" in repost_result:
                logger.info("[✅ REPOST SUCCESS] Tweet repost completed successfully!")
                logger.info("✅ CUA navigation to tweet page working")
                logger.info("✅ Repost dialog opened and confirmed working")
                logger.info("✅ Repost functionality validated")
                all_results.append(("Repost Tweet CUA", "SUCCESS"))
                
            elif "SESSION_INVALIDATED" in repost_result:
                logger.error("[❌ REPOST SESSION ISSUE] Browser session became unauthenticated")
                logger.info("[TIP] Run authentication setup to restore session.")
                all_results.append(("Repost Tweet CUA", "SESSION_INVALIDATED"))
                
            elif "FAILED:" in repost_result:
                logger.error(f"[❌ REPOST FAILED] {repost_result}")
                logger.info("🔍 Check logs for specific failure reason")
                all_results.append(("Repost Tweet CUA", "FAILED"))
                
            else:
                logger.warning(f"[⚠️ REPOST UNKNOWN] Unexpected result format: {repost_result}")
                all_results.append(("Repost Tweet CUA", "UNKNOWN"))
                
        except Exception as e:
            logger.error(f"[❌ REPOST EXCEPTION] Repost test failed with exception: {e}")
            all_results.append(("Repost Tweet CUA", "EXCEPTION"))
        
        # Brief pause between tests
        import time
        time.sleep(3)
        
        # =================================================================
        # TEST 2: FOLLOW USER VIA CUA
        # =================================================================
        logger.info("\n" + "=" * 50)
        logger.info("👤 TEST 2: FOLLOW USER VIA CUA")
        logger.info("=" * 50)
        logger.info(f"Test Profile URL: {test_profile_url}")
        logger.info("Expected: Navigate to profile page, locate and click 'Follow' button")
        logger.info("Success criteria: User followed successfully or proper error handling")
        
        try:
            logger.info("Executing follow_user_via_cua...")
            follow_result = orchestrator.follow_user_via_cua(test_profile_url)
            logger.info(f"Follow CUA Result: {follow_result}")
            
            # Analyze result
            if "SUCCESS:" in follow_result:
                logger.info("[✅ FOLLOW SUCCESS] User follow completed successfully!")
                logger.info("✅ CUA navigation to profile page working")
                logger.info("✅ Follow button detection and clicking working")
                logger.info("✅ Follow functionality validated")
                all_results.append(("Follow User CUA", "SUCCESS"))
                
            elif "SESSION_INVALIDATED" in follow_result:
                logger.error("[❌ FOLLOW SESSION ISSUE] Browser session became unauthenticated")
                logger.info("[TIP] Run authentication setup to restore session.")
                all_results.append(("Follow User CUA", "SESSION_INVALIDATED"))
                
            elif "FAILED:" in follow_result:
                logger.error(f"[❌ FOLLOW FAILED] {follow_result}")
                logger.info("🔍 Check logs for specific failure reason")
                all_results.append(("Follow User CUA", "FAILED"))
                
            else:
                logger.warning(f"[⚠️ FOLLOW UNKNOWN] Unexpected result format: {follow_result}")
                all_results.append(("Follow User CUA", "UNKNOWN"))
                
        except Exception as e:
            logger.error(f"[❌ FOLLOW EXCEPTION] Follow test failed with exception: {e}")
            all_results.append(("Follow User CUA", "EXCEPTION"))
        
        # Brief pause between tests
        time.sleep(3)
        
        # =================================================================
        # TEST 3: SEARCH X FOR TOPIC VIA CUA
        # =================================================================
        logger.info("\n" + "=" * 50)
        logger.info("🔍 TEST 3: SEARCH X FOR TOPIC VIA CUA")
        logger.info("=" * 50)
        logger.info(f"Test Search Query: '{test_search_query}'")
        logger.info("Expected: Use '/' shortcut, enter search query, extract top 3 results")
        logger.info("Success criteria: JSON array of search result tweets or proper error handling")
        
        try:
            logger.info("Executing search_x_for_topic_via_cua...")
            search_result = orchestrator.search_x_for_topic_via_cua(test_search_query, num_results=3)
            logger.info(f"Search CUA Result: {search_result}")
            
            # Analyze result
            if "SUCCESS:" in search_result and "[" in search_result:
                logger.info("[✅ SEARCH SUCCESS] X.com search completed successfully!")
                logger.info("✅ CUA search navigation working")
                logger.info("✅ Search query execution working")
                logger.info("✅ Search results extraction working")
                
                # Try to parse and display the extracted search results
                try:
                    json_match = re.search(r'\[(.*)\]', search_result)
                    if json_match:
                        search_tweets_json = json_match.group(0)
                        search_tweets = json.loads(search_tweets_json)
                        logger.info(f"📋 Extracted {len(search_tweets)} search results:")
                        for i, tweet in enumerate(search_tweets, 1):
                            tweet_preview = tweet[:100] + "..." if len(tweet) > 100 else tweet
                            logger.info(f"  {i}. {tweet_preview}")
                        logger.info("✅ Search results JSON parsing successful")
                    else:
                        logger.info("Could not parse search results JSON, but search completed")
                except Exception as parse_error:
                    logger.warning(f"Could not parse search results JSON: {parse_error}")
                
                all_results.append(("Search X Topic CUA", "SUCCESS"))
                
            elif "SESSION_INVALIDATED" in search_result:
                logger.error("[❌ SEARCH SESSION ISSUE] Browser session became unauthenticated")
                logger.info("[TIP] Run authentication setup to restore session.")
                all_results.append(("Search X Topic CUA", "SESSION_INVALIDATED"))
                
            elif "FAILED:" in search_result:
                logger.error(f"[❌ SEARCH FAILED] {search_result}")
                logger.info("🔍 Check logs for specific failure reason")
                all_results.append(("Search X Topic CUA", "FAILED"))
                
            else:
                logger.warning(f"[⚠️ SEARCH UNKNOWN] Unexpected result format: {search_result}")
                all_results.append(("Search X Topic CUA", "UNKNOWN"))
                
        except Exception as e:
            logger.error(f"[❌ SEARCH EXCEPTION] Search test failed with exception: {e}")
            all_results.append(("Search X Topic CUA", "EXCEPTION"))
        
        # =================================================================
        # COMPREHENSIVE RESULTS ANALYSIS
        # =================================================================
        logger.info("\n" + "=" * 70)
        logger.info("📊 TASK 8.1 RESULTS ANALYSIS - NEW CUA METHODS TESTING")
        logger.info("=" * 70)
        
        success_count = sum(1 for _, result in all_results if result == "SUCCESS")
        total_tests = len(all_results)
        
        logger.info(f"📈 Overall Test Results Summary:")
        for test_name, result in all_results:
            status_emoji = "✅" if result == "SUCCESS" else "❌" if result in ["FAILED", "EXCEPTION"] else "⚠️"
            logger.info(f"  {status_emoji} {test_name}: {result}")
        
        logger.info(f"\n📊 Overall Success Rate: {success_count}/{total_tests} ({success_count/total_tests*100:.1f}%)")
        
        # Detailed analysis
        if success_count == total_tests:
            logger.info("\n🎉 TASK 8.1 VALIDATION: COMPLETE SUCCESS!")
            logger.info("✅ All three new CUA methods implemented and tested successfully")
            logger.info("✅ repost_tweet_via_cua: Working properly")
            logger.info("✅ follow_user_via_cua: Working properly") 
            logger.info("✅ search_x_for_topic_via_cua: Working properly")
            logger.info("✅ CUA integration for all new methods validated")
            logger.info("✅ Task 8.1 requirements fully satisfied")
            logger.info("🚀 Ready to proceed with Sprint 2 next tasks")
            
        elif success_count > 0:
            logger.info("\n⚠️ TASK 8.1 VALIDATION: PARTIAL SUCCESS")
            logger.info(f"✅ {success_count} out of {total_tests} new CUA methods working")
            logger.info("🔍 Some methods may need debugging or refinement")
            
            # Individual method analysis
            for test_name, result in all_results:
                if result == "SUCCESS":
                    logger.info(f"  ✅ {test_name}: Implementation validated")
                elif result == "SESSION_INVALIDATED":
                    logger.info(f"  🔐 {test_name}: Authentication issue detected")
                elif result in ["FAILED", "EXCEPTION"]:
                    logger.info(f"  ❌ {test_name}: Implementation needs debugging")
                else:
                    logger.info(f"  ⚠️ {test_name}: Unexpected result - needs investigation")
            
        else:
            logger.info("\n❌ TASK 8.1 VALIDATION: FAILED")
            logger.info("❌ No new CUA methods working properly")
            logger.info("🔍 All implementations need debugging and refinement")
            logger.info("🔐 Check browser session authentication status")
            logger.info("⚙️ Verify CUA configuration and setup")
        
        # Strategic recommendations
        logger.info("\n🎯 TASK 8.1 STRATEGIC RECOMMENDATIONS:")
        
        session_issues = sum(1 for _, result in all_results if result == "SESSION_INVALIDATED")
        if session_issues > 0:
            logger.info("  🔐 AUTHENTICATION: Browser session authentication issues detected")
            logger.info("    - Run scripts/setup_cua_authentication.py to restore session")
            logger.info("    - Verify X_CUA_USER_DATA_DIR configuration in .env")
            logger.info("    - Ensure browser profile has valid X.com login")
        
        implementation_issues = sum(1 for _, result in all_results if result in ["FAILED", "EXCEPTION"])
        if implementation_issues > 0:
            logger.info(f"  🔧 IMPLEMENTATION: {implementation_issues} methods have implementation issues")
            logger.info("    - Review CUA prompt templates for clarity")
            logger.info("    - Check navigation strategies for each method")
            logger.info("    - Verify error handling and response parsing")
            logger.info("    - Test with alternative URLs/queries")
        
        if success_count == total_tests:
            logger.info("  🚀 NEXT STEPS: Task 8.1 COMPLETED - Ready for Sprint 2 continuation")
            logger.info("    - All new CUA methods (repost, follow, search) validated")
            logger.info("    - Integration with OrchestratorAgent confirmed")
            logger.info("    - CUA prompt refactoring successful")
            logger.info("    - Proceed to next Sprint 2 tasks")
        elif success_count > 0:
            logger.info("  🔄 NEXT STEPS: Complete Task 8.1 validation")
            logger.info("    - Debug and fix failing methods")
            logger.info("    - Re-test all methods for consistency")
            logger.info("    - Ensure all three methods meet success criteria")
        else:
            logger.info("  🔧 NEXT STEPS: Major debugging required")
            logger.info("    - Review CUA system architecture")
            logger.info("    - Verify browser automation setup")
            logger.info("    - Check authentication and configuration")
            logger.info("    - Consider incremental testing approach")
        
        logger.info("\n📋 Task 8.1 Implementation Summary:")
        logger.info("  ✅ repost_tweet_via_cua method added to OrchestratorAgent")
        logger.info("  ✅ follow_user_via_cua method added to OrchestratorAgent")
        logger.info("  ✅ search_x_for_topic_via_cua method added to OrchestratorAgent")
        logger.info("  ✅ CUA instruction templates refactored and moved to core/cua_instructions.py")
        logger.info("  ✅ Constants refactored and moved to core/constants.py")
        logger.info("  ✅ Integration testing implemented in main.py")
        
        # Performance and technical notes
        logger.info("\n🔧 TECHNICAL VALIDATION NOTES:")
        logger.info("Monitor logs for these success indicators:")
        logger.info("  ✅ 'Successfully navigated to [URL]' - Direct navigation working")
        logger.info("  ✅ 'CUA iteration [N]' - CUA interaction loop progressing")
        logger.info("  ✅ 'Acknowledging safety check' - Safety check handling working")
        logger.info("  ✅ 'SUCCESS: [Action] successfully' - Method completed successfully")
        logger.info("  🔧 'FAILED: Could not [action]' - Specific failure points identified")
        logger.info("  🔧 'SESSION_INVALIDATED' - Authentication issues detected")

    except Exception as e:
        logger.error("New CUA methods testing failed: %s", e, exc_info=True)
        logger.error("[CRITICAL FAILED] Test failed due to an unexpected exception. Check your configuration and authentication setup.")
    
    logger.info("X Agentic Unit - Task 8.1 New CUA Methods Testing completed.")


if __name__ == "__main__":
    main()
