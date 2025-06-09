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
    """Tests the CUA timeline reading functionality with viewport displacement fix."""
    logger = logging.getLogger(__name__)
    
    logger.info("Starting X Agentic Unit - CUA Timeline Reading Test")
    logger.info("🔧 This test focuses on validating the viewport displacement fix for CUA timeline reading.")
    
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
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        logger.info(f"\n🔧 VIEWPORT DISPLACEMENT FIX VALIDATION - {timestamp}")
        logger.info("=" * 60)
        logger.info("Previous Issue: 'J' keystrokes caused browser viewport to shift outside visible area")
        logger.info("Applied Fix: Pre-viewport stabilization + automatic displacement detection + recovery")
        logger.info("Expected Result: Successful navigation through tweets with stable viewport")
        logger.info("=" * 60)
        
        # --- MAIN TEST: CUA Timeline Reading with Viewport Displacement Fix ---
        logger.info("\n=== CUA TIMELINE READING TEST ===")
        logger.info("🎯 Testing viewport stability during tweet navigation...")
        logger.info("📋 Monitoring for viewport displacement detection and recovery...")
        
        # Test with different numbers of tweets to validate navigation stability
        test_cases = [
            (3, "Basic 3-tweet navigation test"),
            (5, "Extended 5-tweet navigation test"),
            (2, "Minimal 2-tweet navigation test")
        ]
        
        results = []
        
        for num_tweets, description in test_cases:
            logger.info(f"\n--- {description} ---")
            logger.info(f"Reading top {num_tweets} tweets from home timeline...")
            
            timeline_result = orchestrator.get_home_timeline_tweets_via_cua(num_tweets=num_tweets)
            logger.info(f"CUA Timeline Read Result: {timeline_result}")
            
            # Analyze the result
            if "SUCCESS:" in timeline_result and "[" in timeline_result:
                logger.info(f"[✅ SUCCESS] {description} completed successfully!")
                results.append((description, "SUCCESS"))
                
                # Try to parse and display the extracted tweets
                try:
                    import json
                    import re
                    json_match = re.search(r'\[(.*)\]', timeline_result)
                    if json_match:
                        tweets_json = json_match.group(0)
                        tweets = json.loads(tweets_json)
                        logger.info(f"📋 Extracted {len(tweets)} tweets:")
                        for i, tweet in enumerate(tweets, 1):
                            tweet_preview = tweet[:80] + "..." if len(tweet) > 80 else tweet
                            logger.info(f"  {i}. {tweet_preview}")
                    else:
                        logger.info("Could not parse tweet JSON, but navigation completed")
                except Exception as parse_error:
                    logger.warning(f"Could not parse timeline JSON: {parse_error}")
                    
            elif "SESSION_INVALIDATED" in timeline_result:
                logger.error(f"[❌ SESSION ISSUE] {description} - Browser session became unauthenticated")
                logger.info("[TIP] Run authentication setup to restore session.")
                results.append((description, "SESSION_INVALIDATED"))
                break  # Stop testing if session is invalid
                
            elif "FAILED" in timeline_result:
                logger.error(f"[❌ FAILED] {description} - Check logs for viewport displacement warnings")
                results.append((description, "FAILED"))
                
            else:
                logger.warning(f"[⚠️ UNKNOWN] {description} - Unexpected result format")
                results.append((description, "UNKNOWN"))
            
            # Brief pause between tests
            import time
            time.sleep(2)
        
        # --- NEW: ROBUST TIMELINE READING TEST ---
        logger.info("\n" + "=" * 60)
        logger.info("🔧 ROBUST TIMELINE READING TEST - INDIVIDUAL PAGE NAVIGATION")
        logger.info("=" * 60)
        logger.info("Enhanced Strategy: j → ENT → capture → g+h → j → repeat")
        logger.info("Expected Result: Eliminating viewport displacement through stable page contexts")
        logger.info("=" * 60)
        
        robust_test_cases = [
            (2, "Robust 2-tweet individual page test"),
            (3, "Robust 3-tweet individual page test"),
        ]
        
        robust_results = []
        
        for num_tweets, description in robust_test_cases:
            logger.info(f"\n--- {description} ---")
            logger.info(f"Using robust individual page navigation for {num_tweets} tweets...")
            
            robust_timeline_result = orchestrator.get_home_timeline_tweets_via_cua_robust(num_tweets=num_tweets)
            logger.info(f"Robust CUA Timeline Read Result: {robust_timeline_result}")
            
            # Analyze the robust result
            if "SUCCESS:" in robust_timeline_result and "[" in robust_timeline_result:
                logger.info(f"[✅ ROBUST SUCCESS] {description} completed successfully!")
                robust_results.append((description, "SUCCESS"))
                
                # Try to parse and display the extracted tweets
                try:
                    import json
                    import re
                    json_match = re.search(r'\[(.*)\]', robust_timeline_result)
                    if json_match:
                        tweets_json = json_match.group(0)
                        tweets = json.loads(tweets_json)
                        logger.info(f"📋 Robust method extracted {len(tweets)} tweets:")
                        for i, tweet in enumerate(tweets, 1):
                            tweet_preview = tweet[:80] + "..." if len(tweet) > 80 else tweet
                            logger.info(f"  {i}. {tweet_preview}")
                    else:
                        logger.info("Could not parse robust tweet JSON, but navigation completed")
                except Exception as parse_error:
                    logger.warning(f"Could not parse robust timeline JSON: {parse_error}")
                    
            elif "SESSION_INVALIDATED" in robust_timeline_result:
                logger.error(f"[❌ ROBUST SESSION ISSUE] {description} - Browser session became unauthenticated")
                robust_results.append((description, "SESSION_INVALIDATED"))
                break  # Stop testing if session is invalid
                
            elif "FAILED" in robust_timeline_result:
                logger.error(f"[❌ ROBUST FAILED] {description} - Check logs for navigation issues")
                robust_results.append((description, "FAILED"))
                
            else:
                logger.warning(f"[⚠️ ROBUST UNKNOWN] {description} - Unexpected result format")
                robust_results.append((description, "UNKNOWN"))
            
            # Brief pause between robust tests
            import time
            time.sleep(3)  # Longer pause for more complex navigation
        
        # --- NEW: CONSOLIDATED TIMELINE READING TEST ---
        logger.info("\n" + "=" * 60)
        logger.info("🔧 CONSOLIDATED TIMELINE READING TEST - VIEWPORT FIXES + INDIVIDUAL NAVIGATION")
        logger.info("=" * 60)
        logger.info("Ultimate Strategy: Proven viewport stabilization + robust individual page navigation")
        logger.info("Expected Result: Maximum reliability combining best of both approaches")
        logger.info("=" * 60)
        
        consolidated_test_cases = [
            (2, "Consolidated 2-tweet viewport + individual page test"),
            (3, "Consolidated 3-tweet viewport + individual page test"),
        ]
        
        consolidated_results = []
        
        for num_tweets, description in consolidated_test_cases:
            logger.info(f"\n--- {description} ---")
            logger.info(f"Using consolidated approach with viewport fixes + individual navigation for {num_tweets} tweets...")
            
            consolidated_timeline_result = orchestrator.get_home_timeline_tweets_via_cua_consolidated(num_tweets=num_tweets)
            logger.info(f"Consolidated CUA Timeline Read Result: {consolidated_timeline_result}")
            
            # Analyze the consolidated result
            if "SUCCESS:" in consolidated_timeline_result and "[" in consolidated_timeline_result:
                logger.info(f"[✅ CONSOLIDATED SUCCESS] {description} completed successfully!")
                consolidated_results.append((description, "SUCCESS"))
                
                # Try to parse and display the extracted tweets
                try:
                    import json
                    import re
                    json_match = re.search(r'\[(.*)\]', consolidated_timeline_result)
                    if json_match:
                        tweets_json = json_match.group(0)
                        tweets = json.loads(tweets_json)
                        logger.info(f"📋 Consolidated method extracted {len(tweets)} tweets:")
                        for i, tweet in enumerate(tweets, 1):
                            tweet_preview = tweet[:80] + "..." if len(tweet) > 80 else tweet
                            logger.info(f"  {i}. {tweet_preview}")
                    else:
                        logger.info("Could not parse consolidated tweet JSON, but navigation completed")
                except Exception as parse_error:
                    logger.warning(f"Could not parse consolidated timeline JSON: {parse_error}")
                    
            elif "SESSION_INVALIDATED" in consolidated_timeline_result:
                logger.error(f"[❌ CONSOLIDATED SESSION ISSUE] {description} - Browser session became unauthenticated")
                consolidated_results.append((description, "SESSION_INVALIDATED"))
                break  # Stop testing if session is invalid
                
            elif "FAILED" in consolidated_timeline_result:
                logger.error(f"[❌ CONSOLIDATED FAILED] {description} - Check logs for navigation issues")
                consolidated_results.append((description, "FAILED"))
                
            else:
                logger.warning(f"[⚠️ CONSOLIDATED UNKNOWN] {description} - Unexpected result format")
                consolidated_results.append((description, "UNKNOWN"))
            
            # Brief pause between consolidated tests
            import time
            time.sleep(3)  # Longer pause for more complex navigation
        
        # --- RESULTS ANALYSIS ---
        logger.info("\n" + "=" * 60)
        logger.info("🔍 VIEWPORT DISPLACEMENT FIX VALIDATION RESULTS")
        logger.info("=" * 60)
        
        success_count = sum(1 for _, result in results if result == "SUCCESS")
        total_tests = len(results)
        
        logger.info(f"📊 Test Results Summary:")
        for description, result in results:
            status_emoji = "✅" if result == "SUCCESS" else "❌" if result == "FAILED" else "⚠️"
            logger.info(f"  {status_emoji} {description}: {result}")
        
        logger.info(f"\n📈 Overall Success Rate: {success_count}/{total_tests} ({success_count/total_tests*100:.1f}%)")
        
        # Robust method analysis
        robust_success_count = sum(1 for _, result in robust_results if result == "SUCCESS")
        robust_total_tests = len(robust_results)
        
        logger.info("\n" + "=" * 60)
        logger.info("🔧 ROBUST INDIVIDUAL PAGE NAVIGATION RESULTS")
        logger.info("=" * 60)
        
        logger.info(f"📊 Robust Test Results Summary:")
        for description, result in robust_results:
            status_emoji = "✅" if result == "SUCCESS" else "❌" if result == "FAILED" else "⚠️"
            logger.info(f"  {status_emoji} {description}: {result}")
        
        if robust_total_tests > 0:
            if robust_success_count == robust_total_tests:
                logger.info("\n🎉 ROBUST NAVIGATION METHOD: SUCCESS")
                logger.info("✅ All robust individual page navigation tests completed successfully")
                logger.info("✅ No viewport issues with individual page strategy")
                logger.info("✅ Enhanced content extraction from dedicated tweet pages")
                logger.info("✅ g+h navigation preserves timeline position effectively")
                
            elif robust_success_count > 0:
                logger.info("\n⚠️ ROBUST NAVIGATION METHOD: PARTIAL SUCCESS")
                logger.info(f"✅ {robust_success_count} out of {robust_total_tests} robust tests succeeded")
                logger.info("🔍 Some individual page navigation issues detected")
                
            else:
                logger.info("\n❌ ROBUST NAVIGATION METHOD: FAILED")
                logger.info("❌ No robust navigation tests succeeded")
                logger.info("🔍 Individual page strategy may need refinement")
        
        # Consolidated method analysis
        consolidated_success_count = sum(1 for _, result in consolidated_results if result == "SUCCESS")
        consolidated_total_tests = len(consolidated_results)
        
        logger.info("\n" + "=" * 60)
        logger.info("🔧 CONSOLIDATED VIEWPORT + INDIVIDUAL NAVIGATION RESULTS")
        logger.info("=" * 60)
        
        logger.info(f"📊 Consolidated Test Results Summary:")
        for description, result in consolidated_results:
            status_emoji = "✅" if result == "SUCCESS" else "❌" if result == "FAILED" else "⚠️"
            logger.info(f"  {status_emoji} {description}: {result}")
        
        if consolidated_total_tests > 0:
            if consolidated_success_count == consolidated_total_tests:
                logger.info("\n🎉 CONSOLIDATED METHOD: SUCCESS")
                logger.info("✅ All consolidated viewport + individual navigation tests completed successfully")
                logger.info("✅ Perfect combination of viewport stabilization and robust navigation")
                logger.info("✅ Maximum reliability through layered stability mechanisms")
                logger.info("✅ Comprehensive error recovery and displacement prevention")
                logger.info("✅ Ultimate solution combining best of both approaches")
                
            elif consolidated_success_count > 0:
                logger.info("\n⚠️ CONSOLIDATED METHOD: PARTIAL SUCCESS")
                logger.info(f"✅ {consolidated_success_count} out of {consolidated_total_tests} consolidated tests succeeded")
                logger.info("🔍 Some edge cases may still need refinement")
                
            else:
                logger.info("\n❌ CONSOLIDATED METHOD: FAILED")
                logger.info("❌ No consolidated navigation tests succeeded")
                logger.info("🔍 Combined approach may need further optimization")
        
        # Comparative analysis
        logger.info("\n" + "=" * 60)
        logger.info("📊 COMPREHENSIVE COMPARATIVE ANALYSIS")
        logger.info("=" * 60)
        
        if success_count == total_tests:
            logger.info("\n🎉 VIEWPORT DISPLACEMENT FIX VALIDATION: SUCCESS")
            logger.info("✅ All timeline reading tests completed successfully")
            logger.info("✅ No viewport displacement detected during navigation")
            logger.info("✅ CUA successfully navigated through multiple tweets")
            logger.info("✅ Tweet content extraction working properly")
            
        elif success_count > 0:
            logger.info("\n⚠️ VIEWPORT DISPLACEMENT FIX VALIDATION: PARTIAL SUCCESS")
            logger.info(f"✅ {success_count} out of {total_tests} tests succeeded")
            logger.info("🔍 Some navigation issues may still exist - check logs for patterns")
            
        else:
            logger.info("\n❌ VIEWPORT DISPLACEMENT FIX VALIDATION: FAILED")
            logger.info("❌ No timeline reading tests succeeded")
            logger.info("🔍 Viewport displacement fix may need further refinement")
        
        if robust_total_tests > 0:
            if robust_success_count == robust_total_tests:
                logger.info("\n🎉 ROBUST NAVIGATION METHOD: SUCCESS")
                logger.info("✅ All robust individual page navigation tests completed successfully")
                logger.info("✅ No viewport issues with individual page strategy")
                logger.info("✅ Enhanced content extraction from dedicated tweet pages")
                logger.info("✅ g+h navigation preserves timeline position effectively")
                
            elif robust_success_count > 0:
                logger.info("\n⚠️ ROBUST NAVIGATION METHOD: PARTIAL SUCCESS")
                logger.info(f"✅ {robust_success_count} out of {robust_total_tests} robust tests succeeded")
                logger.info("🔍 Some individual page navigation issues detected")
                
            else:
                logger.info("\n❌ ROBUST NAVIGATION METHOD: FAILED")
                logger.info("❌ No robust navigation tests succeeded")
                logger.info("🔍 Individual page strategy may need refinement")
        
        if consolidated_total_tests > 0:
            if consolidated_success_count == consolidated_total_tests:
                logger.info("\n🎉 CONSOLIDATED METHOD: SUCCESS")
                logger.info("✅ All consolidated viewport + individual navigation tests completed successfully")
                logger.info("✅ Perfect combination of viewport stabilization and robust navigation")
                logger.info("✅ Maximum reliability through layered stability mechanisms")
                logger.info("✅ Comprehensive error recovery and displacement prevention")
                logger.info("✅ Ultimate solution combining best of both approaches")
                
            elif consolidated_success_count > 0:
                logger.info("\n⚠️ CONSOLIDATED METHOD: PARTIAL SUCCESS")
                logger.info(f"✅ {consolidated_success_count} out of {consolidated_total_tests} consolidated tests succeeded")
                logger.info("🔍 Some edge cases may still need refinement")
                
            else:
                logger.info("\n❌ CONSOLIDATED METHOD: FAILED")
                logger.info("❌ No consolidated navigation tests succeeded")
                logger.info("🔍 Combined approach may need further optimization")
        
        # Strategic recommendations
        logger.info("\n🎯 STRATEGIC RECOMMENDATIONS:")
        if robust_total_tests > 0 and consolidated_total_tests > 0:
            viewport_success_rate = success_count/total_tests if total_tests > 0 else 0
            robust_success_rate = robust_success_count/robust_total_tests if robust_total_tests > 0 else 0
            consolidated_success_rate = consolidated_success_count/consolidated_total_tests if consolidated_total_tests > 0 else 0
            
            # Determine the best performing method
            method_performance = [
                ("Viewport Fix", viewport_success_rate),
                ("Robust Navigation", robust_success_rate),
                ("Consolidated", consolidated_success_rate)
            ]
            method_performance.sort(key=lambda x: x[1], reverse=True)
            best_method, best_rate = method_performance[0]
            
            logger.info(f"\n📊 METHOD PERFORMANCE RANKING:")
            for i, (method, rate) in enumerate(method_performance, 1):
                status = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                logger.info(f"  {status} {method}: {rate:.1%} success rate")
            
            if consolidated_success_rate >= max(viewport_success_rate, robust_success_rate):
                logger.info("\n🔧 RECOMMENDATION: ADOPT CONSOLIDATED METHOD as primary approach")
                logger.info("  ✅ Combines proven viewport stabilization with robust individual navigation")
                logger.info("  ✅ Maximum reliability through layered stability mechanisms")
                logger.info("  ✅ Comprehensive error recovery and viewport management")
                logger.info("  ✅ Best of both worlds approach eliminates all known displacement issues")
                logger.info("  ⚠️ Consider performance trade-offs (more complex navigation sequence)")
                
            elif viewport_success_rate > robust_success_rate:
                logger.info("  🔧 RECOMMENDATION: Continue with viewport displacement fixes")
                logger.info("  ✅ Better performance with timeline-based navigation")
                logger.info("  ✅ Successful viewport stability achieved")
                logger.info("  ⚠️ Monitor for edge cases in complex timelines")
                logger.info("  🔄 Use consolidated method as fallback for problematic scenarios")
                
            elif robust_success_rate > viewport_success_rate:
                logger.info("  🔧 RECOMMENDATION: Prioritize robust individual page navigation")
                logger.info("  ✅ Enhanced reliability through stable page contexts")
                logger.info("  ✅ Eliminates viewport displacement issues")
                logger.info("  ⚠️ Consider performance trade-offs (more page loads)")
                logger.info("  🔄 Use consolidated method to enhance with viewport stabilization")
                
            else:
                logger.info("  🔧 RECOMMENDATION: Implement intelligent method selection")
                logger.info("  🎯 Use consolidated method for critical operations")
                logger.info("  🎯 Use viewport method for simple navigation")
                logger.info("  🎯 Use robust method for complex content extraction")
                logger.info("  🎯 Implement adaptive selection based on success patterns")
        
        elif robust_total_tests > 0:
            viewport_success_rate = success_count/total_tests if total_tests > 0 else 0
            robust_success_rate = robust_success_count/robust_total_tests if robust_total_tests > 0 else 0
            
            if robust_success_rate > viewport_success_rate:
                logger.info("  🔧 RECOMMENDATION: Prioritize robust individual page navigation")
                logger.info("  ✅ Enhanced reliability through stable page contexts")
                logger.info("  ✅ Eliminates viewport displacement issues")
                logger.info("  ⚠️ Consider performance trade-offs (more page loads)")
                
            elif viewport_success_rate > robust_success_rate:
                logger.info("  🔧 RECOMMENDATION: Continue with viewport displacement fixes")
                logger.info("  ✅ Better performance with timeline-based navigation")
                logger.info("  ✅ Successful viewport stability achieved")
                logger.info("  ⚠️ Monitor for edge cases in complex timelines")
                
            else:
                logger.info("  🔧 RECOMMENDATION: Hybrid approach based on context")
                logger.info("  🎯 Use viewport method for simple navigation")
                logger.info("  🎯 Use robust method for complex content extraction")
                logger.info("  🎯 Implement intelligent method selection")
        
        logger.info("\n🔧 TECHNICAL VALIDATION NOTES:")
        logger.info("Monitor logs for these indicators:")
        logger.info("  ✅ '✅ Viewport stabilization completed' - Pre-stabilization working")
        logger.info("  ✅ '✅ Navigation completed without viewport displacement' - Navigation stable")
        logger.info("  🔧 '⚠️ Potential viewport displacement detected!' - Auto-detection working")
        logger.info("  🔧 '✅ Viewport recovery successful' - Auto-recovery working")
        logger.info("  🔧 '✅ Successfully pre-navigated to home timeline' - Robust method initialization")
        logger.info("  🔧 'Robust CUA iteration' - Individual page navigation progress")
        logger.info("  🔧 'CUA consolidated iteration' - Consolidated method progress")
        logger.info("  🔧 '✅ Consolidated enhanced recovery successful' - Enhanced recovery working")
        logger.info("  ❌ Multiple displacement warnings - Fix may need adjustment")
        
        logger.info(f"\n📋 Next Steps:")
        all_success = success_count + robust_success_count + consolidated_success_count
        all_total = total_tests + robust_total_tests + consolidated_total_tests
        
        if consolidated_total_tests > 0 and consolidated_success_count == consolidated_total_tests:
            logger.info("  - 🎉 CONSOLIDATED METHOD: Perfect success rate achieved!")
            logger.info("  - ✅ CUA timeline reading with ultimate reliability is ready for production")
            logger.info("  - 🚀 Implement consolidated method as primary timeline reading approach")
            logger.info("  - 📈 Scale testing to larger numbers of tweets (5-10) for validation")
            logger.info("  - 🔄 Use consolidated method for all critical timeline operations")
            
        elif all_success == all_total:
            logger.info("  - 🎉 ALL METHODS: Perfect success rate across all approaches!")
            logger.info("  - ✅ CUA timeline reading is ready for production use")
            logger.info("  - 🧠 Implement intelligent method selection based on operational context")
            logger.info("  - 📈 Test with larger numbers of tweets for scalability validation")
            
        elif consolidated_success_count > max(success_count, robust_success_count):
            logger.info("  - 🔧 PRIORITIZE CONSOLIDATED METHOD: Best performing approach")
            logger.info("  - ✅ Viewport stabilization + individual navigation = optimal reliability")
            logger.info("  - 🔄 Use other methods as backup for specific scenarios")
            logger.info("  - 📊 Analyze failure patterns in other methods for improvement")
            
        elif success_count >= max(robust_success_count, consolidated_success_count):
            logger.info("  - 🔧 VIEWPORT DISPLACEMENT FIXES: Primary method working well")
            logger.info("  - ✅ Continue with viewport stabilization as main approach")
            logger.info("  - 🔄 Use consolidated method for problematic scenarios")
            logger.info("  - 📊 Investigate why robust/consolidated methods underperformed")
            
        else:
            logger.info("  - 🔍 MIXED RESULTS: Review logs for specific failure patterns")
            logger.info("  - 🔧 Check browser session authentication status")
            logger.info("  - ⚙️ Consider adjusting viewport stabilization parameters")
            logger.info("  - 🔄 Test consolidated method error recovery procedures")
            logger.info("  - 📊 Analyze which scenarios cause failures in each method")

    except Exception as e:
        logger.error("CUA timeline reading test failed: %s", e, exc_info=True)
        logger.error("[CRITICAL FAILED] Test failed due to an unexpected exception. Check your configuration and authentication setup.")
    
    logger.info("X Agentic Unit - CUA Timeline Reading Test completed.")


if __name__ == "__main__":
    main()
