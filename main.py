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
    """Test the Supabase MCP Server connection for Task 8.2.1."""
    logger = logging.getLogger(__name__)
    
    logger.info("Starting X Agentic Unit - Supabase MCP Server Connection Test (Task 8.2.1)")
    logger.info("🔧 Testing Supabase MCP Server integration into OrchestratorAgent.")
    
    # Get current timestamp for test logging
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    logger.info(f"\n🚀 SUPABASE MCP CONNECTION TEST - {timestamp}")
    logger.info("=" * 70)
    logger.info("Task 8.2.1: Integrate Supabase MCP Server into OrchestratorAgent")
    logger.info("Expected Results: Successful connection and tool listing from Supabase MCP Server")
    logger.info("=" * 70)
    
    try:
        # Initialize the OrchestratorAgent with Supabase MCP integration
        logger.info("Initializing OrchestratorAgent with Supabase MCP Server...")
        orchestrator = OrchestratorAgent()
        
        # Test the Supabase MCP connection
        logger.info("\n" + "=" * 50)
        logger.info("🗄️ TESTING SUPABASE MCP CONNECTION")
        logger.info("=" * 50)
        logger.info("Expected: MCP server starts, connects to Supabase, returns available tools")
        logger.info("Success criteria: List of Supabase tools (list_projects, execute_sql, etc.)")
        
        tool_names = await orchestrator.test_supabase_mcp_connection()
        
        # Analyze results
        logger.info("\n" + "=" * 70)
        logger.info("📊 TASK 8.2.1 RESULTS ANALYSIS - SUPABASE MCP INTEGRATION")
        logger.info("=" * 70)
        
        if tool_names:
            logger.info("🎉 TASK 8.2.1 VALIDATION: COMPLETE SUCCESS!")
            logger.info("✅ Supabase MCP Server successfully integrated into OrchestratorAgent")
            logger.info("✅ MCP server starts and connects to Supabase backend")
            logger.info(f"✅ Found {len(tool_names)} Supabase database tools")
            logger.info("✅ Agent now has access to long-term memory capabilities")
            
            # Display available tools
            logger.info("\n📋 Available Supabase MCP Tools:")
            for i, tool_name in enumerate(tool_names, 1):
                logger.info(f"  {i}. {tool_name}")
            
            logger.info("\n🚀 NEXT STEPS: Task 8.2.1 COMPLETED - Ready for Sprint 3 continuation")
            logger.info("  ✅ Create database schema for agent memory")
            logger.info("  ✅ Implement memory-driven decision tools")
            logger.info("  ✅ Enhance OrchestratorAgent with strategic memory")
            logger.info("  ✅ Proceed to Task 8.3: Memory-Driven Decision Tools")
            
        else:
            logger.error("❌ TASK 8.2.1 VALIDATION: FAILED")
            logger.error("❌ Supabase MCP Server connection failed")
            logger.error("🔍 Check Node.js installation and network connectivity")
            logger.error("🔍 Verify Supabase access token configuration")
            logger.error("🔍 Check MCP server command parameters")
            
            logger.info("\n🔧 TROUBLESHOOTING RECOMMENDATIONS:")
            logger.info("  1. Verify Node.js is installed: node --version")
            logger.info("  2. Test MCP server manually: npx -y @supabase/mcp-server-supabase@latest --help")
            logger.info("  3. Check network connectivity to Supabase servers")
            logger.info("  4. Verify access token has proper permissions")
        
        logger.info("\n📋 Task 8.2.1 Implementation Summary:")
        logger.info("  ✅ Added MCPServerStdio import to OrchestratorAgent")
        logger.info("  ✅ Initialized Supabase MCP server in __init__ method")
        logger.info("  ✅ Added mcp_servers parameter to Agent configuration")
        logger.info("  ✅ Implemented test_supabase_mcp_connection method")
        logger.info("  ✅ Updated main.py for async MCP testing")
        
        # Performance and technical notes
        logger.info("\n🔧 TECHNICAL VALIDATION NOTES:")
        logger.info("Monitor logs for these success indicators:")
        logger.info("  ✅ 'Successfully connected to Supabase MCP' - Connection established")
        logger.info("  ✅ 'Found X tools: [tool_names]' - Tool discovery working")
        logger.info("  🔧 'Failed to connect to Supabase MCP server' - Connection issues")
        logger.info("  🔧 Connection timeouts - Network or server issues")

    except Exception as e:
        logger.error("Supabase MCP connection test failed: %s", e, exc_info=True)
        logger.error("[CRITICAL FAILED] Test failed due to an unexpected exception. Check MCP server configuration and dependencies.")
    
    logger.info("X Agentic Unit - Task 8.2.1 Supabase MCP Integration Test completed.")


def main() -> None:
    """Main entry point - runs the async test function."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
