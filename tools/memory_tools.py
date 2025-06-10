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
        agent_name: Name of the agent performing the action (will be stored in metadata)
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
        # Prepare metadata - include agent_name in metadata since the table doesn't have that column
        metadata = details or {}
        metadata['agent_name'] = agent_name
        metadata_json = json.dumps(metadata)
        
        # Build SQL query with values directly embedded (MCP doesn't support parameterized queries)
        # Use single quotes and escape any single quotes in the values
        target_escaped = target.replace("'", "''") if target else ""
        result_escaped = result.replace("'", "''")
        action_type_escaped = action_type.replace("'", "''")
        metadata_escaped = metadata_json.replace("'", "''")
        
        sql_query = f"""
        INSERT INTO agent_actions (action_type, target, result, metadata, timestamp)
        VALUES ('{action_type_escaped}', '{target_escaped}', '{result_escaped}', '{metadata_escaped}', NOW())
        RETURNING id, timestamp;
        """
        
        # Execute the SQL via MCP server (no params needed)
        result_data = await server.call_tool(
            "execute_sql",
            {
                "project_id": "vgqkwooelncsckghajpg",  # Our AIified project ID
                "query": sql_query
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
        # Build the SQL query based on filters (no parameterized queries)
        if action_type:
            action_type_escaped = action_type.replace("'", "''")
            sql_query = f"""
            SELECT id, action_type, target, result, metadata, timestamp
            FROM agent_actions
            WHERE action_type = '{action_type_escaped}' 
            AND timestamp > NOW() - INTERVAL '{hours_back} hours'
            ORDER BY timestamp DESC
            LIMIT {limit};
            """
        else:
            sql_query = f"""
            SELECT id, action_type, target, result, metadata, timestamp
            FROM agent_actions  
            WHERE timestamp > NOW() - INTERVAL '{hours_back} hours'
            ORDER BY timestamp DESC
            LIMIT {limit};
            """
        
        # Execute the SQL via MCP server
        result_data = await server.call_tool(
            "execute_sql",
            {
                "project_id": "vgqkwooelncsckghajpg", 
                "query": sql_query
            }
        )
        
        logger.info(f"🔍 Raw MCP result: {result_data}")
        logger.info(f"🔍 Result type: {type(result_data)}")
        
        # Parse the MCP CallToolResult - extract JSON from TextContent
        actions = []
        if hasattr(result_data, 'content') and result_data.content:
            for content_item in result_data.content:
                if hasattr(content_item, 'text'):
                    try:
                        json_data = json.loads(content_item.text)
                        if isinstance(json_data, list):
                            actions = json_data
                        break
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON: {e}")
                        logger.error(f"Raw text: {content_item.text}")
        
        logger.info(f"🔍 Parsed {len(actions)} actions from result")
        
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
        # Prepare values - escape single quotes
        idea_escaped = idea_summary.replace("'", "''")
        source = source_url or source_query or "research"
        source_escaped = source.replace("'", "''")
        
        # Build the SQL query with values directly embedded
        sql_query = f"""
        INSERT INTO content_ideas (idea_text, source, topic_category, relevance_score, created_at)
        VALUES ('{idea_escaped}', '{source_escaped}', """
        
        # Handle optional values
        if topic_category:
            topic_escaped = topic_category.replace("'", "''")
            sql_query += f"'{topic_escaped}'"
        else:
            sql_query += "NULL"
        
        sql_query += ", "
        
        if relevance_score is not None:
            sql_query += str(relevance_score)
        else:
            sql_query += "NULL"
        
        sql_query += ", NOW()) RETURNING id, created_at;"
        
        # Execute the SQL via MCP server
        result_data = await server.call_tool(
            "execute_sql",
            {
                "project_id": "vgqkwooelncsckghajpg",
                "query": sql_query
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
            topic_escaped = topic_category.replace("'", "''")
            sql_query = f"""
            SELECT id, idea_text, source, topic_category, relevance_score, created_at
            FROM content_ideas
            WHERE used = false AND topic_category = '{topic_escaped}'
            ORDER BY relevance_score DESC, created_at DESC
            LIMIT {limit};
            """
        else:
            sql_query = f"""
            SELECT id, idea_text, source, topic_category, relevance_score, created_at
            FROM content_ideas
            WHERE used = false
            ORDER BY relevance_score DESC, created_at DESC
            LIMIT {limit};
            """
        
        # Execute the SQL via MCP server
        result_data = await server.call_tool(
            "execute_sql",
            {
                "project_id": "vgqkwooelncsckghajpg",
                "query": sql_query
            }
        )
        
        # Parse the MCP CallToolResult - extract JSON from TextContent
        ideas = []
        if hasattr(result_data, 'content') and result_data.content:
            for content_item in result_data.content:
                if hasattr(content_item, 'text'):
                    try:
                        json_data = json.loads(content_item.text)
                        if isinstance(json_data, list):
                            ideas = json_data
                        break
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON: {e}")
                        logger.error(f"Raw text: {content_item.text}")
        
        logger.info(f"🔍 Parsed {len(ideas)} ideas from result")
        
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
        sql_query = f"""
        UPDATE content_ideas
        SET used = true
        WHERE id = {idea_id}
        RETURNING id, idea_text;
        """
        
        # Execute the SQL via MCP server
        result_data = await server.call_tool(
            "execute_sql",
            {
                "project_id": "vgqkwooelncsckghajpg",
                "query": sql_query
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
        # Escape the target value
        target_escaped = target.replace("'", "''")
        
        # Build the SQL query based on filters
        if action_types:
            action_types_escaped = [action_type.replace("'", "''") for action_type in action_types]
            action_types_str = "', '".join(action_types_escaped)
            sql_query = f"""
            SELECT id, action_type, result, timestamp, metadata
            FROM agent_actions
            WHERE target = '{target_escaped}' 
            AND action_type IN ('{action_types_str}')
            AND timestamp > NOW() - INTERVAL '{hours_back} hours'
            ORDER BY timestamp DESC;
            """
        else:
            sql_query = f"""
            SELECT id, action_type, result, timestamp, metadata
            FROM agent_actions
            WHERE target = '{target_escaped}'
            AND timestamp > NOW() - INTERVAL '{hours_back} hours'
            ORDER BY timestamp DESC;
            """
        
        logger.info(f"🔍 Memory query: {sql_query}")
        
        # Execute the SQL via MCP server
        result_data = await server.call_tool(
            "execute_sql",
            {
                "project_id": "vgqkwooelncsckghajpg",
                "query": sql_query
            }
        )
        
        logger.info(f"🔍 Raw MCP result: {result_data}")
        logger.info(f"🔍 Result type: {type(result_data)}")
        
        # Parse the MCP CallToolResult - extract JSON from TextContent
        interactions = []
        if hasattr(result_data, 'content') and result_data.content:
            for content_item in result_data.content:
                if hasattr(content_item, 'text'):
                    try:
                        json_data = json.loads(content_item.text)
                        if isinstance(json_data, list):
                            interactions = json_data
                        break
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON: {e}")
                        logger.error(f"Raw text: {content_item.text}")
        
        logger.info(f"🔍 Parsed {len(interactions)} interactions from result")
        
        interaction_count = len(interactions)
        
        # More aggressive spam prevention - skip if ANY recent interaction exists for like_tweet
        if action_types and 'like_tweet' in action_types:
            should_skip = interaction_count >= 1  # Skip if any like_tweet interaction in timeframe
        else:
            should_skip = interaction_count >= 3  # More than 3 interactions for other actions
        
        logger.info(f"✅ Found {interaction_count} recent interactions with {target}")
        if interactions:
            interaction_summary = [f"{i['action_type']}({i['result']})" for i in interactions[:3]]
            logger.info(f"   Recent interactions: {interaction_summary}")
        
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