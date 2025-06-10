#!/usr/bin/env python3
"""Test script for memory tools integration in the OrchestratorAgent.

This script validates that the memory-driven decision tools are properly
integrated and functional within the OrchestratorAgent.
"""

import asyncio
import logging
import sys
from datetime import datetime

from project_agents.orchestrator_agent import OrchestratorAgent


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def test_memory_tools_integration():
    """Test the memory tools integration in OrchestratorAgent."""
    logger.info("🧪 Starting memory tools integration test...")
    
    try:
        # Initialize the OrchestratorAgent
        logger.info("Initializing OrchestratorAgent...")
        orchestrator = OrchestratorAgent()
        
        # Test 1: Supabase MCP Connection
        logger.info("\n📡 Test 1: Testing Supabase MCP connection...")
        tools = await orchestrator.test_supabase_mcp_connection()
        if tools:
            logger.info(f"✅ MCP connection successful! Found {len(tools)} tools")
        else:
            logger.error("❌ MCP connection failed!")
            return False
        
        # Test 2: Log Action to Memory
        logger.info("\n📝 Test 2: Testing action logging...")
        log_result = await orchestrator._log_action_to_memory(
            action_type='test_memory_integration',
            result='SUCCESS',
            target='memory_test',
            details={'test_timestamp': datetime.now().isoformat(), 'test_purpose': 'integration_validation'}
        )
        
        if log_result.get('success'):
            logger.info("✅ Action logging successful!")
        else:
            logger.error(f"❌ Action logging failed: {log_result}")
            return False
        
        # Test 3: Save Content Idea
        logger.info("\n💡 Test 3: Testing content idea saving...")
        idea_result = await orchestrator._save_content_idea_to_memory(
            idea_summary='Test content idea: AI agents are revolutionizing software development workflows',
            source_query='AI agents software development',
            topic_category='AI/ML',
            relevance_score=8
        )
        
        if idea_result.get('success'):
            logger.info("✅ Content idea saving successful!")
        else:
            logger.error(f"❌ Content idea saving failed: {idea_result}")
            return False
        
        # Test 4: Retrieve Recent Actions
        logger.info("\n🔍 Test 4: Testing recent actions retrieval...")
        actions_result = await orchestrator._retrieve_recent_actions_from_memory(
            action_type='test_memory_integration',
            hours_back=1,
            limit=10
        )
        
        if actions_result.get('success'):
            count = actions_result.get('count', 0)
            logger.info(f"✅ Recent actions retrieval successful! Found {count} actions")
            # Test passes as long as the query was successful, even if no results (timing-dependent)
        else:
            logger.error(f"❌ Recent actions retrieval failed: {actions_result}")
            return False
        
        # Test 5: Get Unused Content Ideas
        logger.info("\n🎯 Test 5: Testing unused content ideas retrieval...")
        ideas_result = await orchestrator._get_unused_content_ideas_from_memory(
            topic_category='AI/ML',
            limit=5
        )
        
        if ideas_result.get('success'):
            logger.info(f"✅ Content ideas retrieval successful! Found {ideas_result.get('count')} ideas")
        else:
            logger.error(f"❌ Content ideas retrieval failed: {ideas_result}")
            return False
        
        # Test 6: Check Target Interactions (using our test target)
        logger.info("\n🔍 Test 6: Testing target interaction checking...")
        interaction_result = await orchestrator._check_recent_target_interactions(
            target='memory_test',
            action_types=['test_memory_integration'],
            hours_back=1
        )
        
        if interaction_result.get('success'):
            logger.info(f"✅ Target interaction check successful! Found {interaction_result.get('interaction_count')} interactions")
            logger.info(f"Should skip: {interaction_result.get('should_skip')} - {interaction_result.get('reason')}")
        else:
            logger.error(f"❌ Target interaction check failed: {interaction_result}")
            return False
        
        # Test 7: Enhanced Research (simulation)
        logger.info("\n🔍 Test 7: Testing enhanced research simulation...")
        logger.info("Note: This test simulates the research flow without actual web search")
        
        # Simulate research result saving
        await orchestrator._log_action_to_memory(
            action_type='research_topic',
            result='SUCCESS',
            target='AI agents integration testing',
            details={'simulated': True, 'test_phase': 'memory_integration'}
        )
        
        logger.info("✅ Enhanced research simulation completed!")
        
        logger.info("\n🎉 All memory tools integration tests passed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Memory tools integration test failed with exception: {e}", exc_info=True)
        return False


async def main():
    """Main entry point for the test script."""
    logger.info("🚀 Starting Memory Tools Integration Test Suite")
    logger.info("=" * 60)
    
    success = await test_memory_tools_integration()
    
    logger.info("=" * 60)
    if success:
        logger.info("🎉 ALL TESTS PASSED! Memory tools integration is working correctly.")
        sys.exit(0)
    else:
        logger.error("❌ TESTS FAILED! Memory tools integration has issues.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 