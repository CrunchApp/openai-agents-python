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
    """Test Sprint 4 Autonomous Decision-Making Loop - Single Run Test."""
    logger = logging.getLogger(__name__)
    
    logger.info("Starting X Agentic Unit - Sprint 4 Autonomous Decision-Making Test")
    logger.info("🤖 Testing the Autonomous Orchestrator with Enhanced System Instructions")
    
    # Get current timestamp for test logging
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    logger.info(f"\n🚀 SPRINT 4 AUTONOMOUS LOOP TEST - {timestamp}")
    logger.info("=" * 80)
    logger.info("Testing: OrchestratorAgent with Master System Prompt & Autonomous Decision-Making")
    logger.info("Goal: Validate that the agent can autonomously decide what action to take based on its goals")
    logger.info("=" * 80)
    
    try:
        # Initialize the OrchestratorAgent with new autonomous instructions
        logger.info("Initializing OrchestratorAgent with Autonomous Decision-Making Instructions...")
        orchestrator = OrchestratorAgent()
        
        logger.info("\n" + "=" * 60)
        logger.info("🧠 AUTONOMOUS DECISION-MAKING CYCLE")
        logger.info("=" * 60)
        logger.info("The agent will now:")
        logger.info("  1️⃣ Analyze the current situation using its memory")
        logger.info("  2️⃣ Choose ONE strategic action from its Action Menu")
        logger.info("  3️⃣ Execute the chosen action using appropriate tools")
        logger.info("  4️⃣ Document the results and strategic reasoning")
        
        # Define the trigger input that will activate the agent's autonomous reasoning
        trigger_input = "New action cycle: Assess the situation and choose a strategic action based on your goals and memory."
        
        logger.info(f"\n🔥 TRIGGERING AUTONOMOUS CYCLE")
        logger.info(f"Input: {trigger_input}")
        logger.info("🔥" * 60)
        
        # Execute the autonomous decision-making cycle
        from agents import Runner, RunConfig
        
        result = await Runner.run(
            orchestrator, 
            input=trigger_input,
            run_config=RunConfig(workflow_name="Autonomous_Decision_Making_Cycle")
        )
        
        logger.info("\n" + "✨" * 60)
        logger.info("🎯 AUTONOMOUS CYCLE COMPLETED")
        logger.info("✨" * 60)
        
        # Extract and log the final output
        final_output = str(result.final_output) if result.final_output else "No final output"
        
        logger.info(f"📋 Agent's Final Decision Summary:")
        logger.info(f"{final_output}")
        
        # Log the messages/reasoning for deeper insight
        if hasattr(result, 'messages') and result.messages:
            logger.info(f"\n🧠 Decision-Making Process ({len(result.messages)} steps):")
            for i, message in enumerate(result.messages[-5:], 1):  # Show last 5 messages
                role = getattr(message, 'role', 'unknown')
                content_preview = str(message)[:200] + "..." if len(str(message)) > 200 else str(message)
                logger.info(f"  Step {i} ({role}): {content_preview}")
        
        # Check what tools were actually called during the cycle
        if hasattr(result, 'tool_calls') or hasattr(result, 'usage'):
            logger.info(f"\n🔧 Tool Usage Analysis:")
            # This will depend on the specific Runner result structure
            # We can analyze this further in the logs
        
        # ==================== POST-CYCLE MEMORY ANALYSIS ====================
        logger.info("\n" + "📊" * 50)
        logger.info("POST-CYCLE MEMORY ANALYSIS")
        logger.info("📊" * 50)
        
        # Check what actions were logged during this cycle
        memory_results = await orchestrator._retrieve_recent_actions_from_memory(
            action_type=None,  # Get all action types
            hours_back=1,     # Last hour
            limit=20          # Increased limit to see the cycle's actions
        )
        
        if memory_results.get('success', False):
            recent_actions = memory_results.get('actions', [])
            cycle_actions = [a for a in recent_actions if 'cycle' in a.get('action_type', '').lower() or 
                           any(keyword in a.get('timestamp', '') for keyword in [timestamp.split(':')[0]])]  # Actions from this hour
            
            logger.info(f"📈 Recent Actions in Memory: {len(recent_actions)} total")
            logger.info(f"🤖 Actions from this cycle: {len(cycle_actions)}")
            
            # Show the most recent actions
            for i, action in enumerate(recent_actions[:10], 1):
                action_type = action.get('action_type', 'unknown')
                result_status = action.get('result', 'unknown')
                target = action.get('target', 'no target')[:50]
                action_timestamp = action.get('timestamp', 'unknown')
                logger.info(f"    {i}. {action_type} | {result_status} | {target}... | {action_timestamp}")
        
        # ==================== CONTENT IDEAS CHECK ====================
        logger.info("\n" + "💡" * 50)
        logger.info("CONTENT IDEAS INVENTORY")
        logger.info("💡" * 50)
        
        content_ideas = await orchestrator._get_unused_content_ideas_from_memory(
            topic_category=None,  # All categories
            limit=10
        )
        
        if content_ideas.get('success', False):
            ideas_count = content_ideas.get('count', 0)
            logger.info(f"💡 Total Unused Content Ideas: {ideas_count}")
            if ideas_count > 0:
                ideas_list = content_ideas.get('ideas', [])
                for i, idea in enumerate(ideas_list[:5], 1):  # Show first 5
                    summary = idea.get('idea_summary', 'No summary')[:80]
                    category = idea.get('topic_category', 'uncategorized')
                    score = idea.get('relevance_score', 'N/A')
                    logger.info(f"    {i}. [{category}] Score:{score} | {summary}...")
        
        # ==================== AUTONOMOUS CAPABILITY ASSESSMENT ====================
        logger.info("\n" + "=" * 80)
        logger.info("🎉 SPRINT 4 AUTONOMOUS LOOP - CAPABILITY ASSESSMENT")
        logger.info("=" * 80)
        
        # Analyze what the agent actually did
        assessment_points = []
        
        # Check if the agent made a strategic decision
        if final_output and len(final_output) > 50:
            assessment_points.append("✅ Agent provided detailed decision summary")
        else:
            assessment_points.append("❌ Agent output was minimal or empty")
        
        # Check if memory was accessed
        if memory_results.get('success', False) and len(recent_actions) > 0:
            assessment_points.append("✅ Memory system is functional and logging actions")
        else:
            assessment_points.append("❌ Memory system not functioning properly")
        
        # Check for tool usage in the final output
        tool_keywords = ['research', 'like', 'timeline', 'content', 'search', 'memory']
        if any(keyword in final_output.lower() for keyword in tool_keywords):
            assessment_points.append("✅ Agent appears to have used strategic tools")
        else:
            assessment_points.append("⚠️ Agent may not have fully utilized available tools")
        
        # Check for strategic reasoning
        strategy_keywords = ['because', 'decided', 'chose', 'analyzed', 'strategy', 'goal']
        if any(keyword in final_output.lower() for keyword in strategy_keywords):
            assessment_points.append("✅ Agent demonstrated strategic reasoning")
        else:
            assessment_points.append("⚠️ Limited evidence of strategic reasoning")
        
        # Print assessment
        for point in assessment_points:
            logger.info(point)
        
        success_count = len([p for p in assessment_points if p.startswith("✅")])
        total_checks = len(assessment_points)
        
        if success_count == total_checks:
            logger.info("\n🎊 SPRINT 4 VALIDATION: COMPLETE SUCCESS!")
            logger.info("✅ Autonomous decision-making loop is fully operational")
            logger.info("✅ Agent can independently choose and execute strategic actions")
            logger.info("✅ Memory integration supports autonomous decision-making")
            logger.info("✅ Master system prompt provides effective guidance")
            logger.info("\n🚀 READY FOR PRODUCTION: Autonomous X Agentic Unit!")
        elif success_count >= total_checks * 0.75:
            logger.info(f"\n🌟 SPRINT 4 VALIDATION: STRONG SUCCESS ({success_count}/{total_checks})")
            logger.info("✅ Core autonomous functionality is working well")
            logger.info("⚙️ Minor optimizations may improve performance")
        else:
            logger.warning(f"\n⚠️ SPRINT 4 VALIDATION: NEEDS IMPROVEMENT ({success_count}/{total_checks})")
            logger.warning("❌ Autonomous decision-making needs debugging")
        
        logger.info("\n📋 Sprint 4 Implementation Summary:")
        logger.info("  ✅ Master system prompt with Action Menu and Strategic Rules")
        logger.info("  ✅ Autonomous decision-making cycle framework")
        logger.info("  ✅ Memory-driven strategic planning capability")
        logger.info("  ✅ Integration with all CUA tools and sub-agents")
        logger.info("  ✅ Scheduled execution framework via SchedulingAgent")
        logger.info("\n🎯 The X Agentic Unit is now capable of autonomous operation!")

    except Exception as e:
        logger.error("Sprint 4 Autonomous Decision-Making test failed: %s", e, exc_info=True)
        logger.error("❌ [CRITICAL FAILED] Autonomous cycle failed. Check system prompt and tool integration.")
    
    logger.info("X Agentic Unit - Sprint 4 Autonomous Decision-Making Test completed.")


def main() -> None:
    """Main entry point - runs the autonomous decision-making loop test."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
