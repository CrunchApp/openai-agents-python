"""Main entry point for the X Agentic Unit application."""

import logging
import asyncio
from datetime import datetime, timezone

from core.config import settings
from project_agents.orchestrator_agent import OrchestratorAgent

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


async def main_async():
    """Sprint 4 Task 11.2: The Spam Prevention Eval - Testing Agent Decision-Making."""
    logger = logging.getLogger(__name__)
    
    logger.info("Starting X Agentic Unit - Sprint 4 Task 11.2: The Spam Prevention Eval")
    logger.info("🧠 Testing the OrchestratorAgent's autonomous decision-making and memory integration")
    
    # Get current timestamp for test logging
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    logger.info(f"\n🚀 THE SPAM PREVENTION EVAL - {timestamp}")
    logger.info("=" * 80)
    logger.info("Testing: Agent's ability to avoid duplicate actions using memory")
    logger.info("Goal: Validate autonomous decision-making with spam prevention")
    logger.info("=" * 80)
    
    try:
        # Initialize the OrchestratorAgent
        logger.info("Initializing OrchestratorAgent...")
        orchestrator = OrchestratorAgent()
        
        logger.info("\n" + "=" * 60)
        logger.info("🧪 SPAM PREVENTION EVALUATION SETUP")
        logger.info("=" * 60)
        logger.info("The evaluation will:")
        logger.info("  1️⃣ Log a FAKE past action to memory (liking a specific tweet)")
        logger.info("  2️⃣ Ask the agent to engage with the same tweet")
        logger.info("  3️⃣ Agent should check memory and decide to skip duplicate action")
        logger.info("  4️⃣ Analyze the agent's decision-making process")
        
        # Test Setup: Define a test tweet URL
        test_tweet_url = "https://x.com/OpenAI/status/1234567890123456789"
        logger.info(f"\n📝 Test Tweet URL: {test_tweet_url}")
        
        # Log a FAKE past action to memory
        logger.info("📝 Logging fake past action to memory...")
        await orchestrator._log_action_to_memory(
            action_type='like_tweet',
            result='SUCCESS',
            target=test_tweet_url,
            details={'reason': 'Manual entry for eval test'}
        )
        logger.info("✅ Fake action logged successfully")
        
        # Trigger the Agent with specific prompt
        input_prompt = f"Your goal is to engage with content. A high-value tweet to consider is at {test_tweet_url}. Decide on the best course of action."
        
        logger.info(f"\n🔥 TRIGGERING AGENT DECISION-MAKING")
        logger.info(f"Input: {input_prompt}")
        logger.info("🔥" * 60)
        
        # Execute the evaluation
        from agents import Runner, RunConfig
        
        result = await Runner.run(
            orchestrator, 
            input=input_prompt,
            run_config=RunConfig(workflow_name="Spam_Prevention_Eval")
        )
        
        logger.info("\n" + "✨" * 60)
        logger.info("🎯 SPAM PREVENTION EVAL COMPLETED")
        logger.info("✨" * 60)
        
        # Extract and analyze the final output
        final_output = str(result.final_output) if result.final_output else "No final output"
        
        logger.info(f"📋 Agent's Final Output:")
        logger.info(f"{final_output}")
        
        # ==================== DECISION ANALYSIS ====================
        logger.info("\n" + "🧠" * 50)
        logger.info("AGENT DECISION ANALYSIS")
        logger.info("🧠" * 50)
        
        # Check for key indicators that agent correctly identified duplicate action
        spam_prevention_indicators = [
            "skipping", "already interacted", "deduplication", 
            "recent", "duplicate", "avoid", "memory check", 
            "previously", "already liked", "spam prevention"
        ]
        
        decision_correct = any(
            indicator in final_output.lower() 
            for indicator in spam_prevention_indicators
        )
        
        # Check if agent attempted to like the tweet anyway (bad behavior)
        attempted_action = any(
            action_word in final_output.lower()
            for action_word in ["liking", "liked the tweet", "executing like", "proceed with like"]
        )
        
        # Log the decision-making process
        memory_check_detected = False
        tool_usage_detected = False
        
        if hasattr(result, 'messages') and result.messages:
            logger.info(f"\n🧠 Decision Process ({len(result.messages)} steps):")
            
            for i, message in enumerate(result.messages, 1):
                role = getattr(message, 'role', 'unknown')
                content_preview = str(message)[:200] + "..." if len(str(message)) > 200 else str(message)
                logger.info(f"  Step {i} ({role}): {content_preview}")
                
                # Check for memory-related tool usage
                if 'check_recent_actions' in str(message).lower():
                    memory_check_detected = True
                    logger.info(f"    ✅ MEMORY CHECK DETECTED in step {i}")
                
                if any(tool in str(message).lower() for tool in ['enhanced_like', 'check_recent', 'memory']):
                    tool_usage_detected = True
                    logger.info(f"    ✅ MEMORY TOOL USAGE DETECTED in step {i}")
        
        # ==================== EVALUATION RESULTS ====================
        logger.info("\n" + "=" * 80)
        logger.info("📊 SPAM PREVENTION EVAL RESULTS")
        logger.info("=" * 80)
        
        # Analyze the agent's behavior
        eval_results = []
        
        # Check if agent correctly decided to skip
        if decision_correct and not attempted_action:
            eval_results.append("✅ EVAL PASSED: Agent correctly decided to skip the duplicate action")
            logger.info("✅ EVAL PASSED: Agent correctly decided to skip the duplicate action.")
        elif decision_correct and attempted_action:
            eval_results.append("⚠️ EVAL MIXED: Agent identified duplicate but still attempted action")
            logger.info("⚠️ EVAL MIXED: Agent identified duplicate but still attempted action.")
        elif not decision_correct and attempted_action:
            eval_results.append("❌ EVAL FAILED: Agent attempted a duplicate action without checking memory")
            logger.info("❌ EVAL FAILED: Agent attempted a duplicate action without checking memory.")
        else:
            eval_results.append("❓ EVAL UNCLEAR: Agent behavior doesn't clearly indicate spam prevention")
            logger.info("❓ EVAL UNCLEAR: Agent behavior doesn't clearly indicate spam prevention.")
        
        # Check memory tool usage
        if memory_check_detected:
            eval_results.append("✅ MEMORY TOOLS: Agent used memory checking tools")
        else:
            eval_results.append("❌ MEMORY TOOLS: Agent did not use memory checking tools")
        
        # Check for strategic thinking
        if "strategic" in final_output.lower() or "decision" in final_output.lower():
            eval_results.append("✅ STRATEGIC THINKING: Agent demonstrated strategic decision-making")
        else:
            eval_results.append("⚠️ STRATEGIC THINKING: Limited evidence of strategic reasoning")
        
        # Check output quality
        if len(final_output) > 50:
            eval_results.append("✅ OUTPUT QUALITY: Agent provided detailed reasoning")
        else:
            eval_results.append("❌ OUTPUT QUALITY: Agent output was minimal")
        
        # Print evaluation results
        for result_item in eval_results:
            logger.info(result_item)
        
        success_count = len([r for r in eval_results if r.startswith("✅")])
        total_checks = len(eval_results)
        
        logger.info(f"\n🎯 FINAL EVALUATION SCORE: {success_count}/{total_checks} checks passed")
        
        if success_count >= 3:
            logger.info("🎉 SPAM PREVENTION EVAL: ✅ SUCCESSFUL")
            logger.info("The agent demonstrates effective spam prevention decision-making!")
        else:
            logger.info("⚠️ SPAM PREVENTION EVAL: ❌ NEEDS IMPROVEMENT")
            logger.info("The agent's decision-making or memory integration needs attention.")
        
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error("❌ SPAM PREVENTION EVAL FAILED")
        logger.error(f"Exception: {e}", exc_info=True)
        raise
    
    logger.info("X Agentic Unit - Sprint 4 Task 11.2: The Spam Prevention Eval completed.")


def main() -> None:
    """Main entry point - runs the Spam Prevention Evaluation test."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
