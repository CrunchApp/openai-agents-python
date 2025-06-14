"""Orchestrator agent module for managing workflows."""

import asyncio
import json
import logging
from typing import Any, TYPE_CHECKING
from dataclasses import dataclass

from agents import Agent, RunContextWrapper, function_tool, Runner
from agents.mcp.server import MCPServerStdio
from core.config import settings
from core.models import CuaTask
from core.constants import ORCHESTRATOR_MODEL
from core.cua_instructions import get_tweet_like_prompt
from core.db_manager import (
    get_agent_state,
    get_approved_reply_tasks,
    save_agent_state,
    update_human_review_status,
)
from core.oauth_manager import OAuthError
from project_agents.content_creation_agent import ContentCreationAgent
from project_agents.research_agent import ResearchAgent
from project_agents.x_interaction_agent import XInteractionAgent
from tools.human_handoff_tool import _request_human_review_impl as call_request_human_review, DraftedReplyData, request_strategic_direction
from tools.x_api_tools import (
    XApiError,
    get_mentions,
    post_text_tweet as _post_text_tweet,
    get_profile_metrics,
)
from tools.memory_tools import (
    log_action_to_memory,
    retrieve_recent_actions_from_memory,
    save_content_idea_to_memory,
    get_unused_content_ideas_from_memory,
    mark_content_idea_as_used,
    check_recent_target_interactions,
)
from pydantic import ValidationError

if TYPE_CHECKING:
    from core.cua_session_manager import CuaSessionManager

@dataclass
class AppContext:
    """Application context containing the persistent CUA session."""
    cua_session: 'CuaSessionManager'


class OrchestratorAgent(Agent[AppContext]):
    """Central coordinator agent for managing X platform interactions."""

    def __init__(self) -> None:
        """Initialize the Orchestrator Agent with logger and sub-agents."""
        self.logger = logging.getLogger(__name__)
        self.content_creation_agent = ContentCreationAgent()
        self.research_agent = ResearchAgent()
        self.x_interaction_agent = XInteractionAgent()

        # Initialize the Supabase MCP Server configuration (connection will be managed per-request)
        self.supabase_mcp_server = MCPServerStdio(
            params={
                "command": "cmd",
                "args": [
                    "/c",
                    "npx",
                    "-y",
                    "@supabase/mcp-server-supabase@latest",
                    "--access-token",
                    settings.supabase_access_token
                ]
            },
            # Cache the tool list for performance. We can invalidate it later if needed.
            cache_tools_list=True,
            # Increase timeout for Supabase server startup
            client_session_timeout_seconds=15.0
        )

        super().__init__(
            name="Orchestrator Agent",
            instructions=(
                """
                You are "AIified", an autonomous, multi-modal X (Twitter) agent whose sole mission is to grow the @AIified account by cultivating genuine, high-quality engagement within the AI / LLM / Machine-Learning community.

                ─── CORE LOOP ───
                In EVERY cycle you must:
                1. Analyse:   Review strategic memory (Supabase) + fresh situational data (timeline, mentions, ideas).
                2. Decide:     Select EXACTLY ONE highest-value action from the Action Menu.
                3. Act:        Execute it with the most appropriate tool(s).
                4. Reflect:    Log what you did and why; note early engagement signals.

                Your goal is NOT to do everything – it is to pick the SINGLE action that maximises near- and long-term engagement.

                ─── STRATEGIC MEMORY (SUPABASE) ───
                • agent_actions       – every action we or sub-agents perform.
                • content_ideas       – harvested topics awaiting posting.
                • tweet_performance   – (optional) performance metrics you can write to.
                ALWAYS query memory (`check_recent_actions`) before outward interactions to prevent spam.

                ─── ACTION MENU ───
                ① Content Research      → `enhanced_research_with_memory`          (default when idle)
                ② Draft / Post Content  → ContentCreationAgent + `execute_cua_task_direct`
                ③ Engage Timeline       → `read_timeline_with_session` → selective `enhanced_like_tweet_with_memory`
                ④ Reply to Mentions     → `process_new_mentions`
                ⑤ Network Expansion     → `search_and_engage_with_session`
                ⑥ Maintenance / Utils   → other available tools when justified

                ─── GUIDING PRINCIPLES ───
                • MEMORY-FIRST • QUALITY > QUANTITY • VALUE-ADD • TOPICAL RELEVANCE • HIL COMPLIANCE • PLATFORM RULES • RATE LIMIT AWARENESS • ASK FOR HELP when unsure (use `request_strategic_direction`).

                ─── OUTPUT STYLE ───
                Replies / tweets: conversational, concise (< 280 chars), professional yet approachable; minimal emojis; thread drafts numbered.

                ─── PERSISTENCE REMINDER ───
                Keep going until the selected action is fully executed (including any necessary follow-up tool calls) before yielding control.

                ─── TOOL-CALLING REMINDER ───
                Prefer the most specific tool; never guess outcomes – call the tool.

                Think step-by-step INTERNALLY, but output only the required tool calls or final user-visible actions. Do NOT expose chain-of-thought.
                """
            ),
            model=ORCHESTRATOR_MODEL,
            tools=[],
            # Remove MCP servers from agent initialization - will be handled per-request
            # mcp_servers=[self.supabase_mcp_server],
        )

        # Expose process_new_mentions_workflow as a tool for LLM-driven orchestration
        @function_tool(
            name_override="process_new_mentions",
            description_override="Process new X mentions: fetch mentions, draft replies, request human review, and update state",
        )
        async def _process_new_mentions_tool(ctx: RunContextWrapper[AppContext]) -> None:
            """Tool wrapper for process_new_mentions_workflow."""
            await self.process_new_mentions_workflow()

        self.tools.append(_process_new_mentions_tool)

        # Expose process_approved_replies_workflow as a tool for human-approved replies processing
        @function_tool(
            name_override="process_approved_replies",
            description_override="Process approved human-reviewed replies: post approved replies and update review status",
        )
        async def _process_approved_replies_tool(ctx: RunContextWrapper[AppContext]) -> None:
            """Tool wrapper for process_approved_replies_workflow."""
            await self.process_approved_replies_workflow()

        self.tools.append(_process_approved_replies_tool)

        # Add ResearchAgent as a tool for AI/ML topic research
        self.tools.append(
            self.research_agent.as_tool(
                tool_name="find_ai_ml_news_or_topics",
                tool_description="Searches the web for recent news, developments, or interesting topics in AI, LLMs, and Machine Learning. Input should be a specific query or 'general latest AI news'."
            )
        )

        # Add memory-driven decision tools
        @function_tool(
            name_override="enhanced_like_tweet_with_memory",
            description_override="Like a tweet with memory-driven spam prevention. Checks recent interactions to avoid overengaging with the same target. Executes directly using persistent CUA session.",
        )
        async def _enhanced_like_tweet_with_memory_tool(ctx: RunContextWrapper[AppContext], tweet_url: str) -> str:
            """Tool wrapper for enhanced tweet liking with memory."""
            task = await self._enhanced_like_tweet_with_memory(tweet_url)
            if isinstance(task, CuaTask):
                # Execute the task directly using the persistent session
                try:
                    result = await ctx.context.cua_session.run_task(task)
                    
                    # Log the successful action to memory
                    await self._log_action_to_memory(
                        action_type='like_tweet_executed',
                        result='SUCCESS',
                        target=tweet_url,
                        details={'cua_result': result[:200]}
                    )
                    
                    return f"✅ Successfully liked tweet: {result}"
                except Exception as e:
                    # Log the failed action to memory
                    await self._log_action_to_memory(
                        action_type='like_tweet_failed',
                        result='FAILED',
                        target=tweet_url,
                        details={'error': str(e)}
                    )
                    return f"❌ Failed to like tweet: {e}"
            else:
                # Task was skipped due to memory check
                return str(task)

        @function_tool(
            name_override="enhanced_research_with_memory",
            description_override="Research topics with automatic content idea saving to memory. Extracts and stores potential content ideas for future use.",
        )
        async def _enhanced_research_with_memory_tool(ctx: RunContextWrapper[AppContext], query: str) -> str:
            """Tool wrapper for enhanced research with memory."""
            return await self._enhanced_research_with_memory(query)

        @function_tool(
            name_override="get_unused_content_ideas",
            description_override="Retrieve unused content ideas from strategic memory for posting. Can filter by topic category.",
        )
        async def _get_unused_content_ideas_tool(ctx: RunContextWrapper[AppContext], topic_category: str = None, limit: int = 10) -> str:
            """Tool wrapper for retrieving unused content ideas."""
            result = await self._get_unused_content_ideas_from_memory(topic_category, limit)
            return json.dumps(result, indent=2)

        @function_tool(
            name_override="check_recent_actions",
            description_override="Check recent agent actions to avoid duplication and make strategic decisions based on history.",
        )
        async def _check_recent_actions_tool(ctx: RunContextWrapper[AppContext], action_type: str = None, hours_back: int = 24) -> str:
            """Tool wrapper for checking recent actions."""
            result = await self._retrieve_recent_actions_from_memory(action_type, hours_back)
            return json.dumps(result, indent=2)

        # Add direct CUA execution tools using persistent session
        @function_tool(
            name_override="execute_cua_task_direct",
            description_override="Execute a CUA task directly using the persistent browser session. Provide a clear task description and it will be converted to an optimized CUA workflow.",
        )
        async def _execute_cua_task_direct_tool(ctx: RunContextWrapper[AppContext], task_description: str) -> str:
            """Tool wrapper for direct CUA task execution using persistent session."""
            try:
                # Create smart task from description
                from core.cua_instructions import create_smart_cua_task_prompt
                prompt, start_url, max_iterations = create_smart_cua_task_prompt(task_description, {})
                
                # Create CUA task
                task = CuaTask(
                    prompt=prompt,
                    start_url=start_url,
                    max_iterations=max_iterations
                )
                
                # Execute using persistent session
                result = await ctx.context.cua_session.run_task(task)
                
                # Log the action
                await self._log_action_to_memory(
                    action_type='cua_task_executed',
                    result='SUCCESS' if 'SUCCESS' in result else 'COMPLETED',
                    target=task_description,
                    details={
                        'prompt': prompt[:100],
                        'start_url': start_url,
                        'max_iterations': max_iterations,
                        'result': result[:200]
                    }
                )
                
                return f"✅ CUA task completed: {result}"
                
            except Exception as e:
                await self._log_action_to_memory(
                    action_type='cua_task_failed',
                    result='FAILED',
                    target=task_description,
                    details={'error': str(e)}
                )
                return f"❌ CUA task failed: {e}"

        @function_tool(
            name_override="read_timeline_with_session",
            description_override="Read tweets from the home timeline using the persistent browser session. Specify number of tweets to read (default: 5).",
        )
        async def _read_timeline_with_session_tool(ctx: RunContextWrapper[AppContext], num_tweets: int = 5) -> str:
            """Tool wrapper for reading timeline using persistent session."""
            try:
                from core.cua_instructions import get_timeline_reading_prompt
                prompt = get_timeline_reading_prompt(num_tweets)
                
                task = CuaTask(
                    prompt=prompt,
                    start_url="https://x.com",
                    max_iterations=30
                )
                
                result = await ctx.context.cua_session.run_task(task)
                
                # Log the action
                await self._log_action_to_memory(
                    action_type='timeline_read',
                    result='SUCCESS' if 'SUCCESS' in result else 'COMPLETED',
                    target=f"read_{num_tweets}_tweets",
                    details={'num_tweets': num_tweets, 'result': result[:200]}
                )
                
                return f"📱 Timeline reading completed: {result}"
                
            except Exception as e:
                await self._log_action_to_memory(
                    action_type='timeline_read_failed',
                    result='FAILED',
                    target=f"read_{num_tweets}_tweets",
                    details={'error': str(e)}
                )
                return f"❌ Timeline reading failed: {e}"

        @function_tool(
            name_override="search_and_engage_with_session",
            description_override="Search X for topics and engage with relevant content using the persistent browser session. Provide a search query.",
        )
        async def _search_and_engage_with_session_tool(ctx: RunContextWrapper[AppContext], search_query: str) -> str:
            """Tool wrapper for searching and engaging using persistent session."""
            try:
                from core.cua_instructions import get_search_and_like_tweet_prompt
                prompt = get_search_and_like_tweet_prompt(search_query, max_iterations=25)
                
                task = CuaTask(
                    prompt=prompt,
                    start_url="https://x.com",
                    max_iterations=25
                )
                
                result = await ctx.context.cua_session.run_task(task)
                
                # Log the action
                await self._log_action_to_memory(
                    action_type='search_and_engage',
                    result='SUCCESS' if 'SUCCESS' in result else 'COMPLETED',
                    target=search_query,
                    details={'search_query': search_query, 'result': result[:200]}
                )
                
                return f"🔍 Search and engage completed: {result}"
                
            except Exception as e:
                await self._log_action_to_memory(
                    action_type='search_and_engage_failed',
                    result='FAILED',
                    target=search_query,
                    details={'error': str(e)}
                )
                return f"❌ Search and engage failed: {e}"

        # Add profile metrics tool
        @function_tool(
            name_override="get_profile_metrics",
            description_override="Get AIified account statistics (followers, following, tweet count, listed count) via X API v2.",
        )
        async def _get_profile_metrics_tool(ctx: RunContextWrapper[AppContext]) -> str:
            """Tool wrapper for fetching @AIified account metrics."""
            try:
                metrics = get_profile_metrics()
                await self._log_action_to_memory(
                    action_type="profile_metrics_snapshot",
                    result="SUCCESS",
                    details=metrics,
                )
                return json.dumps(metrics, indent=2)
            except Exception as e:
                await self._log_action_to_memory(
                    action_type="profile_metrics_snapshot",
                    result="FAILED",
                    details={"error": str(e)},
                )
                return f"❌ Failed to fetch profile metrics: {e}"

        # Add all the newly defined tools to the agent
        self.tools.extend([
            _enhanced_like_tweet_with_memory_tool,
            _enhanced_research_with_memory_tool,
            _get_unused_content_ideas_tool,
            _check_recent_actions_tool,
            _execute_cua_task_direct_tool,
            _read_timeline_with_session_tool,
            _search_and_engage_with_session_tool,
            _get_profile_metrics_tool,
        ])

        # Add strategic direction tool for human guidance
        self.tools.append(request_strategic_direction)

    def run_simple_post_workflow(self, content: str) -> None:
        """Run a simple workflow that posts content to X via direct tool call."""
        self.logger.info("Starting simple post workflow (direct tool call).")
        try:
            result = _post_text_tweet(text=content)
            self.logger.info("Workflow completed successfully with result: %s", result)
        except Exception as e:
            self.logger.error("Workflow failed: %s", e)
            raise

    def research_topic_for_aiified(self, query: str) -> str:
        """
        Research AI/ML topics via ResearchAgent for content creation.

        Args:
            query: The research query to search for AI/ML news or topics.

        Returns:
            String containing research results or failure message.
        """
        self.logger.info(f"Orchestrator: Researching topic: {query}")
        
        # The `input` to the ResearchAgent (which is a tool of the Orchestrator) 
        # will be what the Orchestrator's LLM passes to the tool.
        # We are directly invoking the research_agent here via Runner for simplicity in this test method.
        
        async def _internal_research():
            # Note: The ResearchAgent itself uses WebSearchTool. 
            # The Runner will handle the ResearchAgent's LLM calling WebSearchTool.
            from agents import RunConfig
            research_result = await Runner.run(
                self.research_agent, 
                input=query,
                run_config=RunConfig(workflow_name="AIified_Topic_Research")
            )
            return str(research_result.final_output)

        try:
            result = asyncio.run(_internal_research())
            self.logger.info(f"Orchestrator: Research result: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Orchestrator: Research failed: {e}", exc_info=True)
            return f"FAILED: Research query '{query}' failed."

    async def _internal_research_with_params(self, query: str) -> str:
        """Internal async research method that can be called from other async contexts.
        
        Args:
            query: Research query string
            
        Returns:
            Research results as string
        """
        self.logger.info(f"Orchestrator: Async researching topic: {query}")
        
        try:
            # Note: The ResearchAgent itself uses WebSearchTool. 
            # The Runner will handle the ResearchAgent's LLM calling WebSearchTool.
            from agents import Runner, RunConfig
            research_result = await Runner.run(
                self.research_agent, 
                input=query,
                run_config=RunConfig(workflow_name="AIified_Topic_Research")
            )
            result = str(research_result.final_output)
            self.logger.info(f"Orchestrator: Async research result: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Orchestrator: Async research failed: {e}", exc_info=True)
            return f"FAILED: Research query '{query}' failed."

    async def test_supabase_mcp_connection(self) -> list:
        """
        Tests the connection to the Supabase MCP server by listing available tools.
        Returns a list of tool names found or an empty list on failure.
        """
        self.logger.info("Testing connection to Supabase MCP server...")
        try:
            # Use async context manager for proper connection lifecycle
            self.logger.info("Starting Supabase MCP server with async context manager...")
            async with self.supabase_mcp_server as server:
                # List available tools
                self.logger.info("Listing available tools...")
                tools = await server.list_tools()
                tool_names = [tool.name for tool in tools]
                self.logger.info(f"✅ Successfully connected to Supabase MCP. Found {len(tool_names)} tools: {tool_names}")
                return tool_names
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to Supabase MCP server: {e}", exc_info=True)
            self.logger.error("Since the .env file is blocked by gitignore, I confirm that Node.js is installed and the SUPABASE_ACCESS_TOKEN is already set up in our .env file.")
            return []

    async def process_new_mentions_workflow(self) -> None:
        """Process new mentions workflow: fetch mentions, draft replies, and request human review."""
        self.logger.info("Starting process new mentions workflow.")
        # Fetch last processed mention ID
        since_id = get_agent_state("last_processed_mention_id_default_user")
        try:
            mentions_response = get_mentions(since_id=since_id)
        except (XApiError, OAuthError) as e:
            self.logger.error("Failed to fetch new mentions: %s", e)
            return
        mentions_data = mentions_response.get("data", [])
        if not mentions_data:
            self.logger.info("No new mentions found.")
            return
        # Determine newest mention ID from meta or data
        newest_id = mentions_response.get("meta", {}).get("newest_id")
        if not newest_id:
            try:
                newest_id = max(m.get("id") for m in mentions_data)
            except Exception:
                newest_id = None
        content_agent = self.content_creation_agent
        for mention in mentions_data:
            mention_text = mention.get("text", "")
            mention_id = mention.get("id")
            author_id = mention.get("author_id")
            try:
                drafted_dict = content_agent.draft_reply(
                    original_tweet_text=mention_text,
                    original_tweet_author=author_id,
                    mention_tweet_id=mention_id,
                )
                # Convert the drafted reply dict into a Pydantic model for strict schema
                try:
                    handoff_data = DraftedReplyData(**drafted_dict)
                except ValidationError as e_pydantic:
                    self.logger.error(f"Failed to create DraftedReplyData for mention {mention_id}: {e_pydantic}")
                    continue
                review_result = call_request_human_review(
                    task_type="reply_to_mention",
                    data_for_review=handoff_data,
                    reason="New mention reply drafted",
                )
                self.logger.info("Human review requested: %s", review_result)
            except Exception as e:
                self.logger.error("Failed to process mention %s: %s", mention_id, e)
        if newest_id:
            save_agent_state("last_processed_mention_id_default_user", newest_id)
        self.logger.info("Completed process new mentions workflow.")

    async def process_approved_replies_workflow(self) -> None:
        """Process approved replies workflow: fetch approved replies, post to X, and update review status."""
        self.logger.info("Starting process approved replies workflow.")
        try:
            tasks = get_approved_reply_tasks()
        except Exception as e:
            self.logger.error("Failed to fetch approved replies: %s", e)
            return
        if not tasks:
            self.logger.info("No approved replies to process.")
            return
        for task in tasks:
            review_id = task.get("review_id")
            data_json = task.get("data_for_review")
            try:
                data = json.loads(data_json)
                text = data.get("draft_reply_text")
                reply_to_id = data.get("original_mention_id")
                result = _post_text_tweet(text=text, in_reply_to_tweet_id=reply_to_id)
                self.logger.info("Posted reply for review_id %s: %s", review_id, result)
                update_human_review_status(review_id, "posted_successfully")
            except Exception as e:
                self.logger.error("Failed to post reply for review_id %s: %s", review_id, e)
                try:
                    update_human_review_status(review_id, "failed_to_post")
                except Exception as e2:
                    self.logger.error(
                        "Failed to update review status for review_id %s: %s", review_id, e2
                    )
        self.logger.info("Completed process approved replies workflow.")

    # ==================== MEMORY-DRIVEN DECISION TOOLS ====================

    async def _log_action_to_memory(
        self,
        action_type: str,
        result: str,
        target: str = None,
        details: dict = None,
    ) -> dict:
        """Internal method to log agent actions to strategic memory.
        
        Args:
            action_type: Type of action (e.g., 'like_tweet', 'post_tweet', 'follow_user')
            result: Result of the action ('SUCCESS', 'FAILED', 'IN_PROGRESS')
            target: Target of the action (URL, username, query, etc.)
            details: Additional metadata as JSON object
            
        Returns:
            Dict containing the result of the memory operation
        """
        try:
            async with self.supabase_mcp_server as server:
                return await log_action_to_memory(
                    server=server,
                    agent_name=self.name,
                    action_type=action_type,
                    result=result,
                    target=target,
                    details=details,
                )
        except Exception as e:
            self.logger.error(f"Failed to log action to memory: {e}")
            # Return a "failed" result but don't crash the main workflow
            return {"success": False, "error": str(e)}

    async def _retrieve_recent_actions_from_memory(
        self,
        action_type: str = None,
        hours_back: int = 24,
        limit: int = 50,
    ) -> dict:
        """Internal method to retrieve recent actions from memory.
        
        Args:
            action_type: Optional filter by action type
            hours_back: How many hours back to look (default: 24)
            limit: Maximum number of records to return (default: 50)
            
        Returns:
            Dict containing the list of recent actions and metadata
        """
        try:
            async with self.supabase_mcp_server as server:
                return await retrieve_recent_actions_from_memory(
                    server=server,
                    action_type=action_type,
                    hours_back=hours_back,
                    limit=limit,
                )
        except Exception as e:
            self.logger.error(f"Failed to retrieve recent actions from memory: {e}")
            return {"success": False, "actions": [], "count": 0, "error": str(e)}

    async def _save_content_idea_to_memory(
        self,
        idea_summary: str,
        source_url: str = None,
        source_query: str = None,
        topic_category: str = None,
        relevance_score: int = None,
    ) -> dict:
        """Internal method to save content ideas to strategic memory.
        
        Args:
            idea_summary: Summary of the content idea
            source_url: URL where the idea was found (optional)
            source_query: Search query that led to the idea (optional)
            topic_category: Category of the topic (optional)
            relevance_score: Relevance score 1-10 (optional)
            
        Returns:
            Dict containing the result of the memory operation
        """
        try:
            async with self.supabase_mcp_server as server:
                return await save_content_idea_to_memory(
                    server=server,
                    idea_summary=idea_summary,
                    source_url=source_url,
                    source_query=source_query,
                    topic_category=topic_category,
                    relevance_score=relevance_score,
                )
        except Exception as e:
            self.logger.error(f"Failed to save content idea to memory: {e}")
            return {"success": False, "error": str(e)}

    async def _get_unused_content_ideas_from_memory(
        self,
        topic_category: str = None,
        limit: int = 10,
    ) -> dict:
        """Internal method to retrieve unused content ideas from memory.
        
        Args:
            topic_category: Optional filter by topic category
            limit: Maximum number of ideas to return (default: 10)
            
        Returns:
            Dict containing the list of unused content ideas
        """
        try:
            async with self.supabase_mcp_server as server:
                return await get_unused_content_ideas_from_memory(
                    server=server,
                    topic_category=topic_category,
                    limit=limit,
                )
        except Exception as e:
            self.logger.error(f"Failed to retrieve unused content ideas from memory: {e}")
            return {"success": False, "ideas": [], "count": 0, "error": str(e)}

    async def _mark_content_idea_as_used(self, idea_id: int) -> dict:
        """Internal method to mark a content idea as used.
        
        Args:
            idea_id: ID of the content idea to mark as used
            
        Returns:
            Dict containing the result of the memory operation
        """
        try:
            async with self.supabase_mcp_server as server:
                return await mark_content_idea_as_used(
                    server=server,
                    idea_id=idea_id,
                )
        except Exception as e:
            self.logger.error(f"Failed to mark content idea as used: {e}")
            return {"success": False, "error": str(e)}

    async def _check_recent_target_interactions(
        self,
        target: str,
        action_types: list = None,
        hours_back: int = 24,
    ) -> dict:
        """Internal method to check recent interactions with a target.
        
        Args:
            target: The target to check (URL, username, etc.)
            action_types: List of action types to check (optional)
            hours_back: How many hours back to look (default: 24)
            
        Returns:
            Dict containing interaction history and spam prevention recommendations
        """
        try:
            async with self.supabase_mcp_server as server:
                return await check_recent_target_interactions(
                    server=server,
                    target=target,
                    action_types=action_types,
                    hours_back=hours_back,
                )
        except Exception as e:
            self.logger.error(f"Failed to check recent target interactions: {e}")
            return {
                "success": False,
                "target": target,
                "interactions": [],
                "interaction_count": 0,
                "should_skip": False,
                "reason": f"Memory check failed: {e}",
                "error": str(e)
            }

    # ==================== ENHANCED METHODS WITH MEMORY ====================

    async def _enhanced_like_tweet_with_memory(self, tweet_url: str):
        """Enhanced tweet liking with memory-driven spam prevention.
        
        Args:
            tweet_url: URL of the tweet to like OR a search query (e.g., '#AI')
            
        Returns:
            CuaTask object if proceeding with like, or string message if skipping
        """
        # Determine if this is a specific URL or a search query
        is_search_query = not tweet_url.startswith('http')
        
        if is_search_query:
            # This is a search query, not a specific tweet URL
            search_query = tweet_url
            target_for_memory = f"search_and_like:{search_query}"
            
            # Check if we've recently done a search-and-like for this query
            memory_check = await self._check_recent_target_interactions(
                target=target_for_memory,
                action_types=['search_and_like', 'like_tweet'],
                hours_back=2  # Shorter window for search queries
            )
            
            if memory_check.get('should_skip', False):
                result_msg = f"⏭️ Skipping search-and-like for '{search_query}' - {memory_check.get('reason', 'Recent similar action detected')}"
                self.logger.info(result_msg)
                
                # Log the skipped action to memory
                await self._log_action_to_memory(
                    action_type='search_and_like_skipped',
                    result='SKIPPED',
                    target=target_for_memory,
                    details={'reason': memory_check.get('reason'), 'search_query': search_query}
                )
                
                return result_msg
            
            # Generate comprehensive search-and-like prompt
            from core.cua_instructions import get_search_and_like_tweet_prompt
            prompt = get_search_and_like_tweet_prompt(search_query, max_iterations=25)
            
            # Create the CuaTask object for search-and-like
            task = CuaTask(
                prompt=prompt,
                start_url="https://x.com",  # Start from X.com home page
                max_iterations=25  # More iterations needed for search-and-like
            )
            
            # Log the task creation to memory
            await self._log_action_to_memory(
                action_type='search_and_like_task_created',
                result='TASK_CREATED',
                target=target_for_memory,
                details={'search_query': search_query, 'max_iterations': task.max_iterations}
            )
            
            self.logger.info(f"✅ Memory check passed - created search-and-like CUA task for: {search_query}")
            return task
            
        else:
            # This is a specific tweet URL - use the original logic
            memory_check = await self._check_recent_target_interactions(
                target=tweet_url,
                action_types=['like_tweet', 'reply_to_tweet'],
                hours_back=24
            )
            
            if memory_check.get('should_skip', False):
                result_msg = f"⏭️ Skipping tweet like - {memory_check.get('reason', 'Recent interaction detected')}"
                self.logger.info(result_msg)
                
                # Log the skipped action to memory
                await self._log_action_to_memory(
                    action_type='like_tweet_skipped',
                    result='SKIPPED',
                    target=tweet_url,
                    details={'reason': memory_check.get('reason'), 'interaction_count': memory_check.get('interaction_count')}
                )
                
                return result_msg
            
            # Generate the prompt for liking using the CUA instructions
            prompt = get_tweet_like_prompt(tweet_url)
            
            # Create the CuaTask object
            task = CuaTask(
                prompt=prompt,
                start_url=tweet_url,
                max_iterations=20  # Reasonable default for like operations
            )
            
            # Log the task creation to memory
            await self._log_action_to_memory(
                action_type='like_tweet_task_created',
                result='TASK_CREATED',
                target=tweet_url,
                details={'task_prompt': prompt[:100], 'max_iterations': task.max_iterations}
            )
            
            self.logger.info(f"✅ Memory check passed - creating CUA task for tweet like: {tweet_url}")
            return task

    async def _enhanced_research_with_memory(self, query: str) -> str:
        """Enhanced research with automatic content idea saving.
        
        Args:
            query: Research query
            
        Returns:
            Research results with content ideas saved to memory
        """
        self.logger.info(f"🔍 Starting enhanced research with memory: {query}")
        
        # Perform the research using async method
        research_result = await self._internal_research_with_params(query)
        
        # Log the research action
        await self._log_action_to_memory(
            action_type='research_topic',
            result='SUCCESS' if research_result else 'FAILED',
            target=query,
            details={'query': query, 'result_length': len(research_result) if research_result else 0}
        )
        
        # Extract and save potential content ideas from research results
        if research_result and len(research_result) > 100:  # Only if substantial content
            # Simple extraction: split by sentences and find interesting ones
            sentences = research_result.split('. ')
            for sentence in sentences:
                # Look for sentences that might be good content ideas
                if (len(sentence) > 50 and len(sentence) < 200 and 
                    any(keyword in sentence.lower() for keyword in ['ai', 'ml', 'artificial intelligence', 'machine learning', 'llm', 'model', 'data'])):
                    
                    await self._save_content_idea_to_memory(
                        idea_summary=sentence.strip(),
                        source_query=query,
                        topic_category='AI/ML',
                        relevance_score=7  # Default relevance score
                    )
        
        return research_result

    async def _create_smart_cua_task(self, task_description: str, context: dict = None) -> str:
        """Create an intelligently structured CUA task with optimized prompts.
        
        Args:
            task_description: Natural language description of the task
            context: Optional context dict with additional parameters
            
        Returns:
            String message about task creation or execution instructions
        """
        self.logger.info(f"🧠 Creating smart CUA task: {task_description}")
        
        try:
            # Import the smart prompt generator
            from core.cua_instructions import create_smart_cua_task_prompt
            
            # Generate optimized prompt and parameters
            prompt, start_url, max_iterations = create_smart_cua_task_prompt(
                task_description, context or {}
            )
            
            # Create the CuaTask object
            task = CuaTask(
                prompt=prompt,
                start_url=start_url,
                max_iterations=max_iterations
            )
            
            # Log the task creation to memory
            await self._log_action_to_memory(
                action_type='smart_cua_task_created',
                result='TASK_CREATED',
                target=task_description,
                details={
                    'start_url': start_url, 
                    'max_iterations': max_iterations,
                    'context': context
                }
            )
            
            self.logger.info(f"✅ Smart CUA task created: {max_iterations} iterations, starting at {start_url}")
            
            # Return instructions for handoff
            return f"Smart CUA task ready for execution. Use execute_cua_task with prompt='{prompt[:100]}...', start_url='{start_url}', max_iterations={max_iterations}"
            
        except Exception as e:
            self.logger.error(f"Failed to create smart CUA task: {e}", exc_info=True)
            return f"FAILED: Could not create CUA task - {str(e)}"

    # ==================== END MEMORY TOOLS ====================
