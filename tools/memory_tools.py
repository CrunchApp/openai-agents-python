"""Memory tools for strategic decision making via Supabase MCP integration.

This module provides helper functions for the OrchestratorAgent to interact with
its strategic memory stored in Supabase. These functions use the MCP execute_sql
tool to perform database operations for learning and deduplication.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List

from agents.mcp.server import MCPServerStdio


logger = logging.getLogger(__name__)


async def log_action_to_memory(
    server: MCPServerStdio,
    agent_name: str,
    action_type: str,
    result: str,
    target: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Log an agent action to the strategic memory database.
    
    Args:
        server: The MCP server instance for Supabase connection
        agent_name: Name of the agent performing the action
        action_type: Type of action (e.g., 'like_tweet', 'post_tweet', 'follow_user')
        result: Result of the action ('SUCCESS', 'FAILED', 'IN_PROGRESS')
        target: Target of the action (URL, username, query, etc.)
        details: Additional metadata as JSON object
        
    Returns:
        Dict containing the result of the database operation
        
    Raises:
        Exception: If the database operation fails
    """
    logger.info(f"📝 Logging action to memory: {action_type} -> {result}")
    
    try:
        # Prepare the SQL query with parameterized inputs
        sql_query = """
        INSERT INTO agent_actions (agent_name, action_type, target, result, metadata, timestamp)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, timestamp;
        """
        
        # Prepare parameters
        timestamp = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(details) if details else None
        
        params = [
            agent_name,
            action_type, 
            target,
            result,
            metadata_json,
            timestamp
        ]
        
        # Execute the SQL via MCP server
        result_data = await server.call_tool(
            "execute_sql",
            {
                "project_id": "vgqkwooelncsckghajpg",  # Our AIified project ID
                "query": sql_query,
                "params": params
            }
        )
        
        logger.info(f"✅ Action logged successfully: {action_type}")
        return {"success": True, "data": result_data}
        
    except Exception as e:
        logger.error(f"❌ Failed to log action to memory: {e}")
        raise


async def retrieve_recent_actions_from_memory(
    server: MCPServerStdio,
    action_type: Optional[str] = None,
    hours_back: int = 24,
    limit: int = 50,
) -> Dict[str, Any]:
    """Retrieve recent actions from memory to avoid duplication.
    
    Args:
        server: The MCP server instance for Supabase connection
        action_type: Optional filter by action type (e.g., 'like_tweet')
        hours_back: How many hours back to look (default: 24)
        limit: Maximum number of records to return (default: 50)
        
    Returns:
        Dict containing the list of recent actions and metadata
        
    Raises:
        Exception: If the database query fails
    """
    logger.info(f"🔍 Retrieving recent actions: type={action_type}, hours={hours_back}")
    
    try:
        # Build the SQL query based on filters
        # Note: PostgreSQL doesn't support parameterized intervals, so we'll use string formatting for hours
        if action_type:
            sql_query = f"""
            SELECT id, agent_name, action_type, target, result, metadata, timestamp
            FROM agent_actions
            WHERE action_type = $1 
            AND timestamp > NOW() - INTERVAL '{hours_back} hours'
            ORDER BY timestamp DESC
            LIMIT $2;
            """
            params = [action_type, limit]
        else:
            sql_query = f"""
            SELECT id, agent_name, action_type, target, result, metadata, timestamp
            FROM agent_actions  
            WHERE timestamp > NOW() - INTERVAL '{hours_back} hours'
            ORDER BY timestamp DESC
            LIMIT $1;
            """
            params = [limit]
        
        # Execute the SQL via MCP server
        result_data = await server.call_tool(
            "execute_sql",
            {
                "project_id": "vgqkwooelncsckghajpg", 
                "query": sql_query,
                "params": params
            }
        )
        
        # Parse the result
        actions = result_data if isinstance(result_data, list) else []
        
        logger.info(f"✅ Retrieved {len(actions)} recent actions")
        return {
            "success": True, 
            "actions": actions,
            "count": len(actions),
            "filters": {"action_type": action_type, "hours_back": hours_back}
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to retrieve recent actions: {e}")
        raise


async def save_content_idea_to_memory(
    server: MCPServerStdio,
    idea_summary: str,
    source_url: Optional[str] = None,
    source_query: Optional[str] = None,
    topic_category: Optional[str] = None,
    relevance_score: Optional[int] = None,
) -> Dict[str, Any]:
    """Save a content idea to the strategic memory database.
    
    Args:
        server: The MCP server instance for Supabase connection
        idea_summary: Summary of the content idea
        source_url: URL where the idea was found (optional)
        source_query: Search query that led to the idea (optional)
        topic_category: Category of the topic (e.g., 'AI', 'ML', 'tech') (optional)
        relevance_score: Relevance score 1-10 (optional)
        
    Returns:
        Dict containing the result of the database operation
        
    Raises:
        Exception: If the database operation fails
    """
    logger.info(f"💡 Saving content idea to memory: {idea_summary[:50]}...")
    
    try:
        # Note: Based on our schema verification, the table uses different column names
        # than specified in the original request. Using actual schema column names.
        sql_query = """
        INSERT INTO content_ideas (idea_text, source, topic_category, relevance_score, created_at)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, created_at;
        """
        
        # Prepare parameters - combine source_url and source_query into source field
        source = source_url or source_query or "research"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        params = [
            idea_summary,
            source,
            topic_category,
            relevance_score,
            timestamp
        ]
        
        # Execute the SQL via MCP server
        result_data = await server.call_tool(
            "execute_sql",
            {
                "project_id": "vgqkwooelncsckghajpg",
                "query": sql_query,
                "params": params
            }
        )
        
        logger.info(f"✅ Content idea saved successfully")
        return {"success": True, "data": result_data}
        
    except Exception as e:
        logger.error(f"❌ Failed to save content idea to memory: {e}")
        raise


async def get_unused_content_ideas_from_memory(
    server: MCPServerStdio,
    topic_category: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Retrieve unused content ideas from memory for strategic posting.
    
    Args:
        server: The MCP server instance for Supabase connection
        topic_category: Optional filter by topic category
        limit: Maximum number of ideas to return (default: 10)
        
    Returns:
        Dict containing the list of unused content ideas
        
    Raises:
        Exception: If the database query fails
    """
    logger.info(f"🎯 Retrieving unused content ideas: category={topic_category}")
    
    try:
        # Build the SQL query based on filters
        if topic_category:
            sql_query = """
            SELECT id, idea_text, source, topic_category, relevance_score, created_at
            FROM content_ideas
            WHERE used = false AND topic_category = $1
            ORDER BY relevance_score DESC, created_at DESC
            LIMIT $2;
            """
            params = [topic_category, limit]
        else:
            sql_query = """
            SELECT id, idea_text, source, topic_category, relevance_score, created_at
            FROM content_ideas
            WHERE used = false
            ORDER BY relevance_score DESC, created_at DESC
            LIMIT $1;
            """
            params = [limit]
        
        # Execute the SQL via MCP server
        result_data = await server.call_tool(
            "execute_sql",
            {
                "project_id": "vgqkwooelncsckghajpg",
                "query": sql_query,
                "params": params
            }
        )
        
        # Parse the result
        ideas = result_data if isinstance(result_data, list) else []
        
        logger.info(f"✅ Retrieved {len(ideas)} unused content ideas")
        return {
            "success": True,
            "ideas": ideas,
            "count": len(ideas),
            "filters": {"topic_category": topic_category}
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to retrieve unused content ideas: {e}")
        raise


async def mark_content_idea_as_used(
    server: MCPServerStdio,
    idea_id: int,
) -> Dict[str, Any]:
    """Mark a content idea as used to prevent reposting.
    
    Args:
        server: The MCP server instance for Supabase connection
        idea_id: ID of the content idea to mark as used
        
    Returns:
        Dict containing the result of the database operation
        
    Raises:
        Exception: If the database operation fails
    """
    logger.info(f"✔️ Marking content idea {idea_id} as used")
    
    try:
        sql_query = """
        UPDATE content_ideas
        SET used = true
        WHERE id = $1
        RETURNING id, idea_text;
        """
        
        params = [idea_id]
        
        # Execute the SQL via MCP server
        result_data = await server.call_tool(
            "execute_sql",
            {
                "project_id": "vgqkwooelncsckghajpg",
                "query": sql_query,
                "params": params
            }
        )
        
        logger.info(f"✅ Content idea {idea_id} marked as used")
        return {"success": True, "data": result_data}
        
    except Exception as e:
        logger.error(f"❌ Failed to mark content idea as used: {e}")
        raise


async def check_recent_target_interactions(
    server: MCPServerStdio,
    target: str,
    action_types: Optional[List[str]] = None,
    hours_back: int = 24,
) -> Dict[str, Any]:
    """Check if we've recently interacted with a specific target to avoid spam.
    
    Args:
        server: The MCP server instance for Supabase connection
        target: The target to check (URL, username, etc.)
        action_types: List of action types to check (e.g., ['like_tweet', 'reply_to_tweet'])
        hours_back: How many hours back to look (default: 24)
        
    Returns:
        Dict containing interaction history and spam prevention recommendations
        
    Raises:
        Exception: If the database query fails
    """
    logger.info(f"🔍 Checking recent interactions with target: {target}")
    
    try:
        # Build the SQL query based on filters
        if action_types:
            action_types_str = "', '".join(action_types)
            sql_query = f"""
            SELECT id, action_type, result, timestamp, metadata
            FROM agent_actions
            WHERE target = $1 
            AND action_type IN ('{action_types_str}')
            AND timestamp > NOW() - INTERVAL '{hours_back} hours'
            ORDER BY timestamp DESC;
            """
        else:
            sql_query = f"""
            SELECT id, action_type, result, timestamp, metadata
            FROM agent_actions
            WHERE target = $1
            AND timestamp > NOW() - INTERVAL '{hours_back} hours'
            ORDER BY timestamp DESC;
            """
        
        params = [target]
        
        # Execute the SQL via MCP server
        result_data = await server.call_tool(
            "execute_sql",
            {
                "project_id": "vgqkwooelncsckghajpg",
                "query": sql_query,
                "params": params
            }
        )
        
        # Parse the result and generate recommendations
        interactions = result_data if isinstance(result_data, list) else []
        interaction_count = len(interactions)
        
        # Simple spam prevention logic
        should_skip = interaction_count >= 3  # More than 3 interactions in timeframe
        
        logger.info(f"✅ Found {interaction_count} recent interactions with {target}")
        return {
            "success": True,
            "target": target,
            "interactions": interactions,
            "interaction_count": interaction_count,
            "should_skip": should_skip,
            "reason": f"Recently interacted {interaction_count} times in last {hours_back}h" if should_skip else "Safe to interact"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to check recent interactions: {e}")
        raise 