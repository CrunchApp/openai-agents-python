"""Main entry point for running the X Agentic Unit in autonomous mode.

This script initializes the scheduler and starts the autonomous agent that will
run indefinitely, making strategic decisions at regular intervals.
"""

import logging
import time
import asyncio
import sys

# Configure UTF-8 logging FIRST to prevent Unicode errors
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setStream(sys.stdout)
# Ensure UTF-8 encoding for console output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level="INFO",
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        console_handler,
        logging.FileHandler(filename="data/autonomous_agent.log", encoding='utf-8'),
    ],
)

from core.scheduler_setup import initialize_scheduler
from project_agents.scheduling_agent import SchedulingAgent

logger = logging.getLogger(__name__)


def main() -> None:
    """Launch the autonomous X Agentic Unit."""
    logger.info("🚀 LAUNCHING AUTONOMOUS X AGENTIC UNIT 'AIified' 🚀")
    logger.info("=" * 80)
    logger.info("Initializing autonomous agent for continuous operation...")
    logger.info("=" * 80)
    
    try:
        # Initialize the scheduler
        logger.info("📋 Initializing APScheduler...")
        scheduler = initialize_scheduler()
        logger.info("✅ Scheduler initialized successfully")
        
        # Instantiate the scheduling agent
        logger.info("🤖 Creating SchedulingAgent...")
        scheduling_agent = SchedulingAgent(scheduler=scheduler)
        logger.info("✅ SchedulingAgent created successfully")
        
        # Schedule the main autonomous loop (5 minute for close monitoring)
        logger.info("⏰ Scheduling autonomous decision-making cycle (5-minute intervals)...")
        scheduling_agent.schedule_autonomous_cycle(interval_minutes=5)
        logger.info("✅ Autonomous cycle scheduled (every 5 minutes)")
        
        # Schedule maintenance tasks to run alongside the main autonomous cycle
        logger.info("📬 Scheduling mention processing (15-minute intervals)...")
        scheduling_agent.schedule_mention_processing(interval_minutes=15)
        logger.info("✅ Mention processing scheduled (every 15 minutes)")
        
        logger.info("💬 Scheduling approved reply processing (5-minute intervals)...")
        scheduling_agent.schedule_approved_reply_processing(interval_minutes=5)
        logger.info("✅ Approved reply processing scheduled (every 5 minutes)")
        
        # Log successful initialization
        logger.info("\n" + "🎯" * 60)
        logger.info("🎯 AUTONOMOUS AGENT FULLY OPERATIONAL")
        logger.info("🎯" * 60)
        logger.info("📊 Scheduled Jobs:")
        logger.info("  • Autonomous Decision Cycle: Every 5 minutes")
        logger.info("  • Mention Processing: Every 15 minutes")
        logger.info("  • Approved Reply Processing: Every 5 minutes")
        logger.info("")
        logger.info("🤖 The 'AIified' agent is now running autonomously!")
        logger.info("🔄 Next autonomous decision cycle will begin in 5 minutes...")
        logger.info("⏸️  Press Ctrl+C to stop the agent")
        logger.info("🎯" * 60)
        
        # Keep-alive loop to maintain the background scheduler
        try:
            # Keep the main thread alive to allow the background scheduler to run
            while True:
                time.sleep(2)
        except (KeyboardInterrupt, SystemExit):
            logger.info("\n🛑 Shutdown signal received. Shutting down scheduler...")
            scheduler.shutdown()
            logger.info("✅ Scheduler shut down successfully. Exiting.")
            logger.info("👋 Autonomous X Agentic Unit 'AIified' stopped.")
    
    except Exception as e:
        logger.error(f"❌ Error launching autonomous agent: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main() 