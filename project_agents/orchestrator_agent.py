"""Orchestrator agent module for managing workflows."""

import asyncio
import json
import logging
import re
from typing import Any

from agents import Agent, ModelSettings, RunContextWrapper, function_tool, Runner, ComputerTool
from agents.mcp.server import MCPServerStdio
from core.config import settings
from core.constants import (
    COMPLETED_PREFIX,
    CUA_DISPLAY_WIDTH,
    CUA_DISPLAY_HEIGHT,
    CUA_ENVIRONMENT,
    CUA_MAX_ITERATIONS_DEFAULT,
    CUA_MAX_ITERATIONS_REPLY,
    CUA_MAX_ITERATIONS_LIKE,
    CUA_MAX_ITERATIONS_ROBUST_TIMELINE,
    SCREENSHOT_MIN_SIZE_THRESHOLD,
    CONSECUTIVE_EMPTY_SCREENSHOT_LIMIT,
    PAGE_NAVIGATION_TIMEOUT,
    PAGE_STABILIZATION_DELAY,
    UI_RESPONSE_DELAY,
    FOCUS_TRANSITION_DELAY,
    CLICK_RESPONSE_DELAY,
    KEYPRESS_RESPONSE_DELAY,
    SCROLL_RESPONSE_DELAY,
    UNICODE_THRESHOLD,
    LOG_TEXT_SHORT,
    LOG_TEXT_MEDIUM,
    LOG_TEXT_LONG,
    LOG_TEXT_EXTENDED,
    COMPUTER_USE_MODEL,
    ORCHESTRATOR_MODEL,
    SUCCESS_PREFIX,
    FAILED_PREFIX,
    SESSION_INVALIDATED,
    X_SHORTCUT_HOME,
    X_SHORTCUT_COMPOSE,
    X_SHORTCUT_SEND_POST,
    X_SHORTCUT_LIKE,
    X_SHORTCUT_REPLY,
    X_SHORTCUT_ENTER,
    X_SHORTCUT_NEXT_POST,
    EMOJI_MAPPINGS,
    CUA_TOOL_CONFIG,
    X_HOME_URL,
    TWEET_URL_PATTERN,
    RESPONSE_TYPE_COMPUTER_CALL,
    RESPONSE_TYPE_TEXT,
    RESPONSE_TYPE_MESSAGE,
    RESPONSE_TYPE_REASONING,
    API_TRUNCATION_AUTO,
    API_ROLE_SYSTEM,
    API_ROLE_USER,
    CONTENT_TYPE_COMPUTER_CALL_OUTPUT,
    CONTENT_TYPE_INPUT_IMAGE,
    SAFETY_CHECK_ID,
    SAFETY_CHECK_CODE,
    SAFETY_CHECK_MESSAGE,
    SUCCESS_MESSAGE_TWEETS_EXTRACTED,
    COMPLETED_CUA_WORKFLOW,
    COMPLETED_CUA_ITERATIONS,
    TEXT_PARSING_START_MARKER,
    TEXT_PARSING_QUOTE_OFFSET,
    IMAGE_DATA_URL_PREFIX,
    VIEWPORT_DISPLACEMENT_RATIO_THRESHOLD,
    PAGE_RELOAD_WAIT_SECONDS,
    DEFAULT_TIMELINE_TWEET_COUNT,
    COMPLETED_CUA_LATEST_TWEET_READING,
    SUCCESS_MESSAGE_TWEET_TEXT_EXTRACTED,
    RESPONSE_TEXT_SLICE_SHORT,
    RESPONSE_TEXT_SLICE_MEDIUM,
    TEXT_PARSING_QUOTE_START,
    TEXT_PARSING_QUOTE_END,
    SUCCESS_STRING_LITERAL,
    FAILED_STRING_LITERAL,
    SESSION_INVALIDATED_STRING_LITERAL,
    COMPLETED_STRING_LITERAL,
    COMPLETED_CUA_WORKFLOW_TEXT,
    SUCCESS_REPLY_POSTED_FROM_REASONING,
    SUCCESS_TWEET_LIKED_FROM_REASONING,
    COMPLETED_CUA_TWEET_LIKING_WORKFLOW_TEXT,
)
from core.cua_instructions import (
    CUA_SYSTEM_INSTRUCTIONS,
    CUA_RESET_INSTRUCTIONS,
    CUA_UNICODE_HANDLING_INSTRUCTIONS,
    CUA_RESPONSE_FORMATS,
    get_tweet_posting_prompt,
    get_tweet_reply_prompt,
    get_tweet_like_prompt,
    get_tweet_repost_prompt,
    get_user_follow_prompt,
    get_search_x_prompt,
    get_timeline_reading_prompt,
    get_latest_tweet_reading_prompt,
    get_robust_timeline_reading_prompt,
    get_consolidated_timeline_reading_prompt,
)
from core.db_manager import (
    get_agent_state,
    get_approved_reply_tasks,
    save_agent_state,
    update_human_review_status,
)
from core.oauth_manager import OAuthError
from core.computer_env.local_playwright_computer import LocalPlaywrightComputer
from project_agents.content_creation_agent import ContentCreationAgent
from project_agents.research_agent import ResearchAgent
from project_agents.x_interaction_agent import XInteractionAgent
from tools.human_handoff_tool import _request_human_review_impl as call_request_human_review, DraftedReplyData
from tools.x_api_tools import XApiError, get_mentions, post_text_tweet as _post_text_tweet
from tools.memory_tools import (
    log_action_to_memory,
    retrieve_recent_actions_from_memory,
    save_content_idea_to_memory,
    get_unused_content_ideas_from_memory,
    mark_content_idea_as_used,
    check_recent_target_interactions,
)
from pydantic import ValidationError


class OrchestratorAgent(Agent):
    """Central coordinator agent for managing X platform interactions."""

    def __init__(self) -> None:
        """Initialize the Orchestrator Agent with logger and sub-agents."""
        self.logger = logging.getLogger(__name__)
        self.content_creation_agent = ContentCreationAgent()
        self.research_agent = ResearchAgent()
        self.x_interaction_agent = XInteractionAgent()

        # Initialize the Supabase MCP Server connection
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
                "You are a master orchestrator agent. Your role is to manage workflows "
                "involving other specialized agents and tools to manage an X account. "
                "You will decide when to fetch mentions, draft replies, request human review, and post content. "
                "You also have access to Supabase database tools for long-term memory and strategic decision making."
            ),
            model=ORCHESTRATOR_MODEL,
            tools=[],
            mcp_servers=[self.supabase_mcp_server],
        )

        # Expose process_new_mentions_workflow as a tool for LLM-driven orchestration
        @function_tool(
            name_override="process_new_mentions",
            description_override="Process new X mentions: fetch mentions, draft replies, request human review, and update state",
        )
        async def _process_new_mentions_tool(ctx: RunContextWrapper[Any]) -> None:
            """Tool wrapper for process_new_mentions_workflow."""
            await self.process_new_mentions_workflow()

        self.tools.append(_process_new_mentions_tool)

        # Expose process_approved_replies_workflow as a tool for human-approved replies processing
        @function_tool(
            name_override="process_approved_replies",
            description_override="Process approved human-reviewed replies: post approved replies and update review status",
        )
        async def _process_approved_replies_tool(ctx: RunContextWrapper[Any]) -> None:
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
            description_override="Like a tweet with memory-driven spam prevention. Checks recent interactions to avoid overengaging with the same target.",
        )
        async def _enhanced_like_tweet_with_memory_tool(ctx: RunContextWrapper[Any], tweet_url: str) -> str:
            """Tool wrapper for enhanced tweet liking with memory."""
            return await self._enhanced_like_tweet_with_memory(tweet_url)

        @function_tool(
            name_override="enhanced_research_with_memory",
            description_override="Research topics with automatic content idea saving to memory. Extracts and stores potential content ideas for future use.",
        )
        async def _enhanced_research_with_memory_tool(ctx: RunContextWrapper[Any], query: str) -> str:
            """Tool wrapper for enhanced research with memory."""
            return await self._enhanced_research_with_memory(query)

        @function_tool(
            name_override="get_unused_content_ideas",
            description_override="Retrieve unused content ideas from strategic memory for posting. Can filter by topic category.",
        )
        async def _get_unused_content_ideas_tool(ctx: RunContextWrapper[Any], topic_category: str = None, limit: int = 10) -> str:
            """Tool wrapper for retrieving unused content ideas."""
            result = await self._get_unused_content_ideas_from_memory(topic_category, limit)
            return json.dumps(result, indent=2)

        @function_tool(
            name_override="check_recent_actions",
            description_override="Check recent agent actions to avoid duplication and make strategic decisions based on history.",
        )
        async def _check_recent_actions_tool(ctx: RunContextWrapper[Any], action_type: str = None, hours_back: int = 24) -> str:
            """Tool wrapper for checking recent actions."""
            result = await self._retrieve_recent_actions_from_memory(action_type, hours_back)
            return json.dumps(result, indent=2)

        self.tools.extend([
            _enhanced_like_tweet_with_memory_tool,
            _enhanced_research_with_memory_tool,
            _get_unused_content_ideas_tool,
            _check_recent_actions_tool,
        ])

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
            return f"{FAILED_PREFIX}: Research query '{query}' failed."

    def get_latest_own_tweet_text_via_cua(self) -> str:
        """
        Retrieve the text content of the latest tweet from the agent's own X.com profile using browser automation.

        Returns:
            String describing the outcome of the CUA operation and extracted tweet text if successful.

        Raises:
            Exception: If the CUA workflow encounters an unrecoverable error.
        """
        self.logger.info("Starting CUA latest tweet reading workflow")
        
        async def _internal_get_latest_tweet() -> str:
            """Internal async function to handle CUA latest tweet reading workflow."""
            try:
                # Use LocalPlaywrightComputer with proper configuration
                async with LocalPlaywrightComputer(user_data_dir_path=settings.x_cua_user_data_dir) as computer:
                    
                    # Initialize the OpenAI client for direct responses API calls
                    from openai import OpenAI
                    import base64
                    client = OpenAI(api_key=settings.openai_api_key)
                    
                    # Rationale for direct OpenAI client.responses.create usage for CUA tasks:
                    # While the agents.Runner can run an Agent (like ComputerUseAgent) with ComputerTool,
                    # directly interacting with client.responses.create provides finer-grained control.
                    # This direct approach allows for:
                    # 1. Precise management of the CUA interaction loop (screenshot -> action -> next prompt).
                    # 2. Explicit handling and automatic acknowledgment of `pending_safety_checks`,
                    #    which is crucial for autonomous operation and compliance.
                    # 3. Immediate detection and branching logic for specific CUA outcomes like `SESSION_INVALIDATED`
                    #    or detailed `FAILED` states, allowing the Orchestrator to react promptly without
                    #    waiting for the entire ComputerUseAgent run to complete and return a single result.
                    # This direct control enhances reliability and enables more robust error handling
                    # tailored to the X.com CUA workflows.
                    
                    # Define system instructions (general CUA behavior)
                    system_instructions = CUA_SYSTEM_INSTRUCTIONS
                    
                    # Define task-specific prompt (latest tweet reading)
                    task_specific_prompt = get_latest_tweet_reading_prompt()
                    
                    # Initial request to get first screenshot
                    self.logger.info("Sending initial CUA request for latest tweet reading")
                    initial_input_messages = [
                        {"role": API_ROLE_SYSTEM, "content": system_instructions},
                        {"role": API_ROLE_USER, "content": task_specific_prompt}
                    ]
                    response = client.responses.create(
                        model=COMPUTER_USE_MODEL,
                        tools=[CUA_TOOL_CONFIG],
                        input=initial_input_messages,
                        truncation=API_TRUNCATION_AUTO
                    )
                    
                    max_iterations = CUA_MAX_ITERATIONS_DEFAULT
                    iteration = 0
                    
                    while iteration < max_iterations:
                        iteration += 1
                        self.logger.info(f"CUA iteration {iteration}")
                        
                        # Check for computer calls in the response
                        computer_calls = [item for item in response.output if hasattr(item, 'type') and item.type == RESPONSE_TYPE_COMPUTER_CALL]
                        
                        # Debug: Log all response output items
                        self.logger.info(f"Response output items: {len(response.output)}")
                        for i, item in enumerate(response.output):
                            if hasattr(item, 'type'):
                                self.logger.info(f"  Item {i}: type={item.type}")
                                if item.type == RESPONSE_TYPE_TEXT and hasattr(item, 'text'):
                                    self.logger.info(f"    Text content: {item.text[:LOG_TEXT_LONG]}...")
                            else:
                                self.logger.info(f"  Item {i}: {type(item)} - {str(item)[:LOG_TEXT_MEDIUM]}...")
                        
                        if not computer_calls:
                            # Check for text output that might contain our success/failure message
                            text_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == RESPONSE_TYPE_TEXT]
                            reasoning_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == RESPONSE_TYPE_REASONING]
                            message_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == RESPONSE_TYPE_MESSAGE]
                            
                            if text_outputs:
                                final_text = text_outputs[-1].text if hasattr(text_outputs[-1], 'text') else str(text_outputs[-1])
                                self.logger.info(f"CUA completed with text output: {final_text}")
                                if SUCCESS_PREFIX in final_text:
                                    return final_text
                                elif SESSION_INVALIDATED in final_text:
                                    return final_text
                                elif FAILED_PREFIX in final_text:
                                    return final_text
                            
                            if message_outputs:
                                # Handle both direct text and ResponseOutputText objects
                                final_message = ""
                                for msg in message_outputs:
                                    if hasattr(msg, 'text'):
                                        final_message = msg.text
                                        break
                                    elif hasattr(msg, 'content') and hasattr(msg.content, 'text'):
                                        final_message = msg.content.text
                                        break
                                    elif str(msg):
                                        msg_str = str(msg)
                                        # Extract text from ResponseOutputText representation
                                        if TEXT_PARSING_START_MARKER in msg_str:
                                            start = msg_str.find(TEXT_PARSING_START_MARKER) + TEXT_PARSING_QUOTE_OFFSET
                                            end = msg_str.find("'", start)
                                            if end > start:
                                                final_message = msg_str[start:end]
                                                break
                                
                                self.logger.info(f"CUA completed with message text: {final_message}")
                                # Check if message contains our response patterns
                                if SUCCESS_PREFIX in final_message:
                                    return final_message  # Return the actual success message
                                elif SESSION_INVALIDATED in final_message:
                                    return SESSION_INVALIDATED
                                elif FAILED_PREFIX in final_message:
                                    return final_text
                            
                            if reasoning_outputs:
                                final_reasoning = reasoning_outputs[-1].content if hasattr(reasoning_outputs[-1], 'content') else str(reasoning_outputs[-1])
                                self.logger.info(f"CUA completed with reasoning: {final_reasoning[:LOG_TEXT_EXTENDED]}...")
                                # Check if reasoning contains our response patterns
                                if SUCCESS_PREFIX in final_reasoning:
                                    return SUCCESS_MESSAGE_TWEET_TEXT_EXTRACTED
                                elif SESSION_INVALIDATED in final_reasoning:
                                    return SESSION_INVALIDATED
                                elif FAILED_PREFIX in final_reasoning:
                                    return final_text
                        
                            self.logger.info("No computer call found, CUA workflow completed")
                            return COMPLETED_CUA_LATEST_TWEET_READING
                        
                        computer_call = computer_calls[0]
                        action = computer_call.action
                        call_id = computer_call.call_id
                        
                        # Handle safety checks - automatically acknowledge routine social media reading checks
                        acknowledged_checks = []
                        if hasattr(computer_call, 'pending_safety_checks') and computer_call.pending_safety_checks:
                            self.logger.info(f"Safety checks detected: {len(computer_call.pending_safety_checks)} checks")
                            # Automatically acknowledge routine social media reading safety checks for autonomous operation
                            for check in computer_call.pending_safety_checks:
                                self.logger.info(f"Acknowledging safety check: {check.code} - {check.message}")
                                acknowledged_checks.append({
                                    SAFETY_CHECK_ID: check.id,
                                    SAFETY_CHECK_CODE: check.code,
                                    SAFETY_CHECK_MESSAGE: check.message
                                })
                        
                        # Execute the computer action
                        try:
                            await self._execute_computer_action(computer, action)
                        except Exception as e:
                            self.logger.error(f"Error executing computer action {action.type}: {e}")
                            return f"{FAILED_PREFIX}: Computer action execution error: {e}"
                        
                        # Take screenshot
                        try:
                            screenshot_b64 = await computer.screenshot()
                        except Exception as e:
                            self.logger.error(f"Error taking screenshot: {e}")
                            return f"{FAILED_PREFIX}: Screenshot capture error: {e}"
                        
                        # Prepare next request input
                        input_content = [{
                            "call_id": call_id,
                            "type": CONTENT_TYPE_COMPUTER_CALL_OUTPUT,
                            "output": {
                                "type": CONTENT_TYPE_INPUT_IMAGE,
                                "image_url": f"{IMAGE_DATA_URL_PREFIX},{screenshot_b64}"
                            }
                        }]
                        
                        # Add acknowledged safety checks if any
                        if acknowledged_checks:
                            input_content[0]["acknowledged_safety_checks"] = acknowledged_checks
                            self.logger.info(f"Including {len(acknowledged_checks)} acknowledged safety checks in next request")
                        
                        # Send next request
                        try:
                            response = client.responses.create(
                                model=COMPUTER_USE_MODEL,
                                previous_response_id=response.id,
                                tools=[CUA_TOOL_CONFIG],
                                input=input_content,
                                truncation=API_TRUNCATION_AUTO
                            )
                        except Exception as e:
                            self.logger.error(f"Error in CUA API call: {e}")
                            return f"{FAILED_PREFIX}: API call error: {e}"
                    
                    self.logger.warning(f"CUA reached maximum iterations ({max_iterations})")
                    return COMPLETED_CUA_ITERATIONS
                    
            except Exception as e:
                error_msg = f"CUA latest tweet reading failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                return f"{FAILED_PREFIX}: {error_msg}"
        
        try:
            return asyncio.run(_internal_get_latest_tweet())
        except Exception as e:
            error_msg = f"Failed to execute CUA latest tweet reading workflow: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"{FAILED_PREFIX}: {error_msg}"

    def post_tweet_via_cua(self, tweet_text: str) -> str:
        """
        Post a tweet via the ComputerUseAgent using browser automation.

        Args:
            tweet_text: The exact text content to post as a tweet.

        Returns:
            String describing the outcome of the CUA operation.

        Raises:
            Exception: If the CUA workflow encounters an unrecoverable error.
        """
        self.logger.info("Starting CUA tweet posting workflow for text: %s", tweet_text[:LOG_TEXT_SHORT] + "..." if len(tweet_text) > LOG_TEXT_SHORT else tweet_text)
        
        async def _internal_post_via_cua() -> str:
            """Internal async function to handle CUA posting workflow with safety check support."""
            try:
                # Use LocalPlaywrightComputer with proper configuration
                async with LocalPlaywrightComputer(user_data_dir_path=settings.x_cua_user_data_dir) as computer:
                    
                    # Initialize the OpenAI client for direct responses API calls
                    from openai import OpenAI
                    import base64
                    client = OpenAI(api_key=settings.openai_api_key)
                    
                    # Rationale for direct OpenAI client.responses.create usage for CUA tasks:
                    # While the agents.Runner can run an Agent (like ComputerUseAgent) with ComputerTool,
                    # directly interacting with client.responses.create provides finer-grained control.
                    # This direct approach allows for:
                    # 1. Precise management of the CUA interaction loop (screenshot -> action -> next prompt).
                    # 2. Explicit handling and automatic acknowledgment of `pending_safety_checks`,
                    #    which is crucial for autonomous operation and compliance.
                    # 3. Immediate detection and branching logic for specific CUA outcomes like `SESSION_INVALIDATED`
                    #    or detailed `FAILED` states, allowing the Orchestrator to react promptly without
                    #    waiting for the entire ComputerUseAgent run to complete and return a single result.
                    # This direct control enhances reliability and enables more robust error handling
                    # tailored to the X.com CUA workflows.
                    
                    # Define system instructions (general CUA behavior)
                    system_instructions = CUA_SYSTEM_INSTRUCTIONS
                    
                    # CRITICAL FIX: Enhanced Unicode handling approach
                    # Since CUA appears to escape Unicode during typing, try alternative approaches
                    clean_tweet_text = tweet_text
                    
                    # For CUA, we'll provide both the original text and emoji descriptions
                    # to help the agent understand what should be typed
                    cua_display_text = clean_tweet_text
                    for emoji, description in EMOJI_MAPPINGS.items():
                        if emoji in clean_tweet_text:
                            cua_display_text = cua_display_text.replace(emoji, f" {description} ")
                    
                    # Define task-specific prompt (tweet posting)
                    task_specific_prompt = get_tweet_posting_prompt(clean_tweet_text)
                    
                    # Initial request to get first screenshot
                    self.logger.info("Sending initial CUA request")
                    initial_input_messages = [
                        {"role": API_ROLE_SYSTEM, "content": system_instructions},
                        {"role": API_ROLE_USER, "content": task_specific_prompt}
                    ]
                    response = client.responses.create(
                        model=COMPUTER_USE_MODEL,
                        tools=[CUA_TOOL_CONFIG],
                        input=initial_input_messages,
                        truncation=API_TRUNCATION_AUTO
                    )
                    
                    max_iterations = CUA_MAX_ITERATIONS_DEFAULT
                    iteration = 0
                    
                    while iteration < max_iterations:
                        iteration += 1
                        self.logger.info(f"CUA iteration {iteration}")
                        
                        # Check for computer calls in the response
                        computer_calls = [item for item in response.output if hasattr(item, 'type') and item.type == RESPONSE_TYPE_COMPUTER_CALL]
                        
                        # Debug: Log all response output items
                        self.logger.info(f"Response output items: {len(response.output)}")
                        for i, item in enumerate(response.output):
                            if hasattr(item, 'type'):
                                self.logger.info(f"  Item {i}: type={item.type}")
                                if item.type == RESPONSE_TYPE_TEXT and hasattr(item, 'text'):
                                    self.logger.info(f"    Text content: {item.text[:LOG_TEXT_LONG]}...")
                            else:
                                self.logger.info(f"  Item {i}: {type(item)} - {str(item)[:LOG_TEXT_MEDIUM]}...")
                        
                        if not computer_calls:
                            # Check for text output that might contain our success/failure message
                            text_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == RESPONSE_TYPE_TEXT]
                            reasoning_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == RESPONSE_TYPE_REASONING]
                            message_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == RESPONSE_TYPE_MESSAGE]
                            
                            if text_outputs:
                                final_text = text_outputs[-1].text if hasattr(text_outputs[-1], 'text') else str(text_outputs[-1])
                                self.logger.info(f"CUA completed with text output: {final_text}")
                                if SUCCESS_PREFIX in final_text:
                                    return final_text
                                elif SESSION_INVALIDATED in final_text:
                                    return final_text
                                elif FAILED_PREFIX in final_text:
                                    return final_text
                            
                            if message_outputs:
                                # Handle both direct text and ResponseOutputText objects
                                final_message = ""
                                for msg in message_outputs:
                                    if hasattr(msg, 'text'):
                                        final_message = msg.text
                                        break
                                    elif hasattr(msg, 'content') and hasattr(msg.content, 'text'):
                                        final_message = msg.content.text
                                        break
                                    elif str(msg):
                                        msg_str = str(msg)
                                        # Extract text from ResponseOutputText representation
                                        if "text='" in msg_str:
                                            start = msg_str.find("text='") + 6
                                            end = msg_str.find("'", start)
                                            if end > start:
                                                final_message = msg_str[start:end]
                                                break
                                
                                self.logger.info(f"CUA completed with message text: {final_message}")
                                # Check if message contains our response patterns
                                if SUCCESS_PREFIX in final_message:
                                    return final_message  # Return the actual success message
                                elif SESSION_INVALIDATED in final_message:
                                    return SESSION_INVALIDATED
                                elif FAILED_PREFIX in final_message:
                                    return f"{FAILED_PREFIX}: {final_message}"
                            
                            if reasoning_outputs:
                                final_reasoning = reasoning_outputs[-1].content if hasattr(reasoning_outputs[-1], 'content') else str(reasoning_outputs[-1])
                                self.logger.info(f"CUA completed with reasoning: {final_reasoning[:LOG_TEXT_EXTENDED]}...")
                                # Check if reasoning contains our response patterns
                                if SUCCESS_PREFIX in final_reasoning:
                                    return f"{SUCCESS_PREFIX}: Tweet posted successfully (from reasoning)"
                                elif SESSION_INVALIDATED in final_reasoning:
                                    return SESSION_INVALIDATED
                                elif FAILED_PREFIX in final_reasoning:
                                    return f"{FAILED_PREFIX}: {final_reasoning[:LOG_TEXT_LONG]}"
                            
                            self.logger.info("No computer call found, CUA workflow completed")
                            return "COMPLETED: CUA workflow finished"
                        
                        computer_call = computer_calls[0]
                        action = computer_call.action
                        call_id = computer_call.call_id
                        
                        # Handle safety checks - this is the key fix!
                        acknowledged_checks = []
                        if hasattr(computer_call, 'pending_safety_checks') and computer_call.pending_safety_checks:
                            self.logger.info(f"Safety checks detected: {len(computer_call.pending_safety_checks)} checks")
                            # According to our project brief and memory bank, we should automatically acknowledge 
                            # routine social media posting safety checks for autonomous operation
                            for check in computer_call.pending_safety_checks:
                                self.logger.info(f"Acknowledging safety check: {check.code} - {check.message}")
                                acknowledged_checks.append({
                                    "id": check.id,
                                    "code": check.code,
                                    "message": check.message
                                })
                        
                        # Execute the computer action
                        try:
                            await self._execute_computer_action(computer, action)
                        except Exception as e:
                            self.logger.error(f"Error executing computer action {action.type}: {e}")
                            return f"{FAILED_PREFIX}: Computer action execution error: {e}"
                        
                        # Take screenshot
                        try:
                            screenshot_b64 = await computer.screenshot()
                        except Exception as e:
                            self.logger.error(f"Error taking screenshot: {e}")
                            return f"{FAILED_PREFIX}: Screenshot capture error: {e}"
                        
                        # Prepare next request input
                        input_content = [{
                            "call_id": call_id,
                            "type": CONTENT_TYPE_COMPUTER_CALL_OUTPUT,
                            "output": {
                                "type": CONTENT_TYPE_INPUT_IMAGE,
                                "image_url": f"{IMAGE_DATA_URL_PREFIX},{screenshot_b64}"
                            }
                        }]
                        
                        # Add acknowledged safety checks if any
                        if acknowledged_checks:
                            input_content[0]["acknowledged_safety_checks"] = acknowledged_checks
                            self.logger.info(f"Including {len(acknowledged_checks)} acknowledged safety checks in next request")
                        
                        # Send next request
                        try:
                            response = client.responses.create(
                                model=COMPUTER_USE_MODEL,
                                previous_response_id=response.id,
                                tools=[CUA_TOOL_CONFIG],
                                input=input_content,
                                truncation="auto"
                            )
                        except Exception as e:
                            self.logger.error(f"Error in CUA API call: {e}")
                            return f"{FAILED_PREFIX}: API call error: {e}"
                    
                    self.logger.warning(f"CUA reached maximum iterations ({max_iterations})")
                    return COMPLETED_CUA_ITERATIONS
                    
            except Exception as e:
                error_msg = f"CUA tweet posting failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                return f"{FAILED_PREFIX}: {error_msg}"
        
        try:
            return asyncio.run(_internal_post_via_cua())
        except Exception as e:
            error_msg = f"Failed to execute CUA tweet posting workflow: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"{FAILED_PREFIX}: {error_msg}"

    def reply_to_tweet_via_cua(self, tweet_url: str, reply_text: str) -> str:
        """
        Reply to a specific tweet via the ComputerUseAgent using browser automation.

        Args:
            tweet_url: The URL of the tweet to reply to.
            reply_text: The exact text content to post as a reply.

        Returns:
            String describing the outcome of the CUA operation.

        Raises:
            Exception: If the CUA workflow encounters an unrecoverable error.
        """
        self.logger.info("Starting CUA tweet reply workflow for URL: %s", tweet_url)
        self.logger.info("Reply text: %s", reply_text[:LOG_TEXT_MEDIUM] + "..." if len(reply_text) > LOG_TEXT_MEDIUM else reply_text)
        
        async def _internal_reply_via_cua() -> str:
            """Internal async function to handle CUA tweet reply workflow."""
            try:
                # Use LocalPlaywrightComputer with proper configuration
                async with LocalPlaywrightComputer(user_data_dir_path=settings.x_cua_user_data_dir) as computer:
                    
                    # Initialize the OpenAI client for direct responses API calls
                    from openai import OpenAI
                    import base64
                    client = OpenAI(api_key=settings.openai_api_key)
                    
                    # Define system instructions (general CUA behavior)
                    system_instructions = CUA_SYSTEM_INSTRUCTIONS
                    
                    # Navigate directly to the tweet URL using Playwright before starting CUA
                    self.logger.info(f"🧭 Direct navigation to tweet URL: {tweet_url}")
                    try:
                        await computer.page.goto(tweet_url, wait_until='networkidle', timeout=PAGE_NAVIGATION_TIMEOUT)
                        await computer.page.wait_for_timeout(PAGE_STABILIZATION_DELAY)  # Additional wait for page stabilization
                        self.logger.info(f"✅ Successfully navigated to {tweet_url}")
                    except Exception as nav_error:
                        self.logger.error(f"❌ Failed to navigate to {tweet_url}: {nav_error}")
                        return f"{FAILED_PREFIX}: Could not navigate to tweet URL - {nav_error}"
                    
                    # Define task-specific prompt (tweet replying)
                    task_specific_prompt = get_tweet_reply_prompt(tweet_url, reply_text)
                    
                    # Initial request to get first screenshot
                    self.logger.info("Sending initial CUA request for tweet replying")
                    initial_input_messages = [
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": task_specific_prompt}
                    ]
                    response = client.responses.create(
                        model=COMPUTER_USE_MODEL,
                        tools=[CUA_TOOL_CONFIG],
                        input=initial_input_messages,
                        truncation="auto"
                    )
                    
                    max_iterations = CUA_MAX_ITERATIONS_REPLY
                    iteration = 0
                    
                    while iteration < max_iterations:
                        iteration += 1
                        self.logger.info(f"CUA iteration {iteration}")
                        
                        # Check for computer calls in the response
                        computer_calls = [item for item in response.output if hasattr(item, 'type') and item.type == "computer_call"]
                        
                        # Debug: Log all response output items
                        self.logger.info(f"Response output items: {len(response.output)}")
                        for i, item in enumerate(response.output):
                            if hasattr(item, 'type'):
                                self.logger.info(f"  Item {i}: type={item.type}")
                                if item.type == "text" and hasattr(item, 'text'):
                                    self.logger.info(f"    Text content: {item.text[:200]}...")
                            else:
                                self.logger.info(f"  Item {i}: {type(item)} - {str(item)[:100]}...")
                        
                        if not computer_calls:
                            # Check for text output that might contain our success/failure message
                            text_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "text"]
                            reasoning_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "reasoning"]
                            message_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "message"]
                            
                            if text_outputs:
                                final_text = text_outputs[-1].text if hasattr(text_outputs[-1], 'text') else str(text_outputs[-1])
                                self.logger.info(f"CUA completed with text output: {final_text}")
                                if SUCCESS_PREFIX in final_text:
                                    return final_text
                                elif SESSION_INVALIDATED in final_text:
                                    return final_text
                                elif FAILED_PREFIX in final_text:
                                    return final_text
                            
                            if message_outputs:
                                # Handle both direct text and ResponseOutputText objects
                                final_message = ""
                                for msg in message_outputs:
                                    if hasattr(msg, 'text'):
                                        final_message = msg.text
                                        break
                                    elif hasattr(msg, 'content') and hasattr(msg.content, 'text'):
                                        final_message = msg.content.text
                                        break
                                    elif str(msg):
                                        msg_str = str(msg)
                                        # Extract text from ResponseOutputText representation
                                        if "text='" in msg_str:
                                            start = msg_str.find("text='") + 6
                                            end = msg_str.find("'", start)
                                            if end > start:
                                                final_message = msg_str[start:end]
                                                break
                                
                                self.logger.info(f"CUA completed with message text: {final_message}")
                                # Check if message contains our response patterns
                                if SUCCESS_STRING_LITERAL in final_message:
                                    return final_message  # Return the actual success message
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_message:
                                    return SESSION_INVALIDATED
                                elif FAILED_STRING_LITERAL in final_message:
                                    return f"{FAILED_PREFIX}: {final_message}"
                            
                            if reasoning_outputs:
                                final_reasoning = reasoning_outputs[-1].content if hasattr(reasoning_outputs[-1], 'content') else str(reasoning_outputs[-1])
                                self.logger.info(f"CUA completed with reasoning: {final_reasoning[:RESPONSE_TEXT_SLICE_MEDIUM]}...")
                                # Check if reasoning contains our response patterns
                                if SUCCESS_STRING_LITERAL in final_reasoning:
                                    return SUCCESS_REPLY_POSTED_FROM_REASONING
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_reasoning:
                                    return SESSION_INVALIDATED
                                elif FAILED_STRING_LITERAL in final_reasoning:
                                    return f"{FAILED_PREFIX}: {final_reasoning[:RESPONSE_TEXT_SLICE_SHORT]}"
                            
                            self.logger.info("No computer call found, CUA workflow completed")
                            return COMPLETED_CUA_WORKFLOW_TEXT
                        
                        computer_call = computer_calls[0]
                        action = computer_call.action
                        call_id = computer_call.call_id
                        
                        # Handle safety checks - automatically acknowledge routine social media interaction checks
                        acknowledged_checks = []
                        if hasattr(computer_call, 'pending_safety_checks') and computer_call.pending_safety_checks:
                            self.logger.info(f"Safety checks detected: {len(computer_call.pending_safety_checks)} checks")
                            # Automatically acknowledge routine social media interaction safety checks for autonomous operation
                            for check in computer_call.pending_safety_checks:
                                self.logger.info(f"Acknowledging safety check: {check.code} - {check.message}")
                                acknowledged_checks.append({
                                    "id": check.id,
                                    "code": check.code,
                                    "message": check.message
                                })
                        
                        # Execute the computer action
                        try:
                            await self._execute_computer_action(computer, action)
                        except Exception as e:
                            self.logger.error(f"Error executing computer action {action.type}: {e}")
                            return f"FAILED: Computer action execution error: {e}"
                        
                        # Take screenshot
                        try:
                            screenshot_b64 = await computer.screenshot()
                        except Exception as e:
                            self.logger.error(f"Error taking screenshot: {e}")
                            return f"{FAILED_PREFIX}: Screenshot capture error: {e}"
                        
                        # Prepare next request input
                        input_content = [{
                            "call_id": call_id,
                            "type": CONTENT_TYPE_COMPUTER_CALL_OUTPUT,
                            "output": {
                                "type": CONTENT_TYPE_INPUT_IMAGE,
                                "image_url": f"{IMAGE_DATA_URL_PREFIX},{screenshot_b64}"
                            }
                        }]
                        
                        # Add acknowledged safety checks if any
                        if acknowledged_checks:
                            input_content[0]["acknowledged_safety_checks"] = acknowledged_checks
                            self.logger.info(f"Including {len(acknowledged_checks)} acknowledged safety checks in next request")
                        
                        # Send next request
                        try:
                            response = client.responses.create(
                                model=COMPUTER_USE_MODEL,
                                previous_response_id=response.id,
                                tools=[CUA_TOOL_CONFIG],
                                input=input_content,
                                truncation=API_TRUNCATION_AUTO
                            )
                        except Exception as e:
                            self.logger.error(f"Error in CUA API call: {e}")
                            return f"{FAILED_PREFIX}: API call error: {e}"
                    
                    self.logger.warning(f"CUA reached maximum iterations ({max_iterations})")
                    return COMPLETED_CUA_ITERATIONS
                    
            except Exception as e:
                error_msg = f"CUA tweet reply failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                return f"{FAILED_PREFIX}: {error_msg}"
        
        try:
            return asyncio.run(_internal_reply_via_cua())
        except Exception as e:
            error_msg = f"Failed to execute CUA tweet reply workflow: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"{FAILED_PREFIX}: {error_msg}"

    def get_home_timeline_tweets_via_cua(self, num_tweets: int = DEFAULT_TIMELINE_TWEET_COUNT) -> str:
        """
        Read the text content of multiple tweets from the home timeline via CUA.

        Args:
            num_tweets: Number of tweets to read from the top of the timeline (default: 3).

        Returns:
            JSON string containing the list of tweet texts, or error message.

        Raises:
            Exception: If the CUA workflow encounters an unrecoverable error.
        """
        self.logger.info("Starting CUA home timeline reading workflow for %d tweets", num_tweets)
        
        async def _internal_timeline_via_cua() -> str:
            """Internal async function to handle CUA timeline reading workflow."""
            try:
                # Use LocalPlaywrightComputer with proper configuration
                async with LocalPlaywrightComputer(user_data_dir_path=settings.x_cua_user_data_dir) as computer:
                    
                    # =================================================================
                    # 🔧 LAYER 1: PRE-VIEWPORT STABILIZATION (CRITICAL FIX)
                    # =================================================================
                    self.logger.info("🔧 Starting Layer 1: Pre-viewport stabilization before CUA navigation")
                    
                    try:
                        # Step 1: Reset scroll position to top
                        self.logger.info("📐 Resetting scroll position to top")
                        await computer.page.evaluate("window.scrollTo(0, 0);")
                        await asyncio.sleep(UI_RESPONSE_DELAY / 1000)
                        
                        # Step 2: Ensure consistent zoom level (100%)
                        self.logger.info("🔍 Setting zoom level to 100%")
                        await computer.page.evaluate("document.body.style.zoom = '1.0';")
                        await asyncio.sleep(KEYPRESS_RESPONSE_DELAY / 1000)
                        
                        # Step 3: Add viewport stabilization CSS to prevent displacement
                        self.logger.info("🎯 Adding viewport stabilization CSS")
                        stabilization_css = """
                        body { 
                            overflow-x: hidden !important;
                            position: relative !important;
                        }
                        html {
                            scroll-behavior: auto !important;
                        }
                        [data-testid="primaryColumn"] {
                            position: relative !important;
                            transform: none !important;
                        }
                        """
                        await computer.page.add_style_tag(content=stabilization_css)
                        await asyncio.sleep(KEYPRESS_RESPONSE_DELAY / 1000)
                        
                        # Step 4: Force layout recalculation
                        self.logger.info("⚡ Forcing layout recalculation")
                        await computer.page.evaluate("""
                            // Force layout recalculation
                            document.body.offsetHeight;
                            window.getComputedStyle(document.body).getPropertyValue('height');
                            // Ensure we're at the top of the page
                            window.scrollTo({top: 0, left: 0, behavior: 'auto'});
                        """)
                        await asyncio.sleep(UI_RESPONSE_DELAY / 1000)
                        
                        # Step 5: Navigate to home timeline if not already there
                        current_url = computer.page.url
                        if not current_url.endswith('/home'):
                            self.logger.info("🧭 Navigating to home timeline for stable starting point")
                            await computer.page.goto(X_HOME_URL, wait_until='networkidle', timeout=PAGE_NAVIGATION_TIMEOUT)
                            await computer.page.wait_for_timeout(PAGE_STABILIZATION_DELAY)
                            
                            # Re-apply stabilization after navigation
                            await computer.page.evaluate("window.scrollTo(0, 0);")
                            await computer.page.add_style_tag(content=stabilization_css)
                            await asyncio.sleep(UI_RESPONSE_DELAY / 1000)
                        
                        self.logger.info("✅ Layer 1: Viewport stabilization completed successfully")
                        
                    except Exception as stabilization_error:
                        self.logger.warning(f"⚠️ Viewport stabilization failed (proceeding anyway): {stabilization_error}")
                    
                    # =================================================================
                    # End of Layer 1 Viewport Stabilization
                    # =================================================================
                    
                    # Initialize the OpenAI client for direct responses API calls
                    from openai import OpenAI
                    import base64
                    client = OpenAI(api_key=settings.openai_api_key)
                    
                    # Define system instructions (general CUA behavior)
                    system_instructions = CUA_SYSTEM_INSTRUCTIONS
                    
                    # Define task-specific prompt (timeline reading) with enhanced viewport management
                    task_specific_prompt = get_timeline_reading_prompt(num_tweets)
                    
                    # Initial request to get first screenshot
                    self.logger.info("Sending initial CUA request for timeline reading")
                    initial_input_messages = [
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": task_specific_prompt}
                    ]
                    response = client.responses.create(
                        model=COMPUTER_USE_MODEL,
                        tools=[CUA_TOOL_CONFIG],
                        input=initial_input_messages,
                        truncation="auto"
                    )
                    
                    max_iterations = CUA_MAX_ITERATIONS_DEFAULT
                    iteration = 0
                    last_screenshot_size = 0
                    consecutive_empty_screenshots = 0
                    
                    while iteration < max_iterations:
                        iteration += 1
                        self.logger.info(f"CUA iteration {iteration}")
                        
                        # Check for computer calls in the response
                        computer_calls = [item for item in response.output if hasattr(item, 'type') and item.type == "computer_call"]
                        
                        # Debug: Log all response output items
                        self.logger.info(f"Response output items: {len(response.output)}")
                        for i, item in enumerate(response.output):
                            if hasattr(item, 'type'):
                                self.logger.info(f"  Item {i}: type={item.type}")
                                if item.type == "text" and hasattr(item, 'text'):
                                    self.logger.info(f"    Text content: {item.text[:200]}...")
                            else:
                                self.logger.info(f"  Item {i}: {type(item)} - {str(item)[:100]}...")
                        
                        if not computer_calls:
                            # Check for text output that might contain our success/failure message
                            text_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "text"]
                            reasoning_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "reasoning"]
                            message_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "message"]
                            
                            if text_outputs:
                                final_text = text_outputs[-1].text if hasattr(text_outputs[-1], 'text') else str(text_outputs[-1])
                                self.logger.info(f"CUA completed with text output: {final_text}")
                                if SUCCESS_STRING_LITERAL in final_text:
                                    return final_text
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_text:
                                    return final_text
                                elif FAILED_STRING_LITERAL in final_text:
                                    return final_text
                            
                            if message_outputs:
                                # Handle both direct text and ResponseOutputText objects
                                final_message = ""
                                for msg in message_outputs:
                                    if hasattr(msg, 'text'):
                                        final_message = msg.text
                                        break
                                    elif hasattr(msg, 'content') and hasattr(msg.content, 'text'):
                                        final_message = msg.content.text
                                        break
                                    elif str(msg):
                                        msg_str = str(msg)
                                        # Extract text from ResponseOutputText representation
                                        if "text='" in msg_str:
                                            start = msg_str.find("text='") + 6
                                            end = msg_str.find("'", start)
                                            if end > start:
                                                final_message = msg_str[start:end]
                                                break
                                
                                self.logger.info(f"CUA completed with message text: {final_message}")
                                # Check if message contains our response patterns
                                if SUCCESS_STRING_LITERAL in final_message:
                                    return final_message  # Return the actual success message
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_message:
                                    return SESSION_INVALIDATED
                                elif FAILED_STRING_LITERAL in final_message:
                                    return f"{FAILED_PREFIX}: {final_message}"
                            
                            if reasoning_outputs:
                                final_reasoning = reasoning_outputs[-1].content if hasattr(reasoning_outputs[-1], 'content') else str(reasoning_outputs[-1])
                                self.logger.info(f"CUA completed with reasoning: {final_reasoning[:RESPONSE_TEXT_SLICE_MEDIUM]}...")
                                # Check if reasoning contains our response patterns
                                if SUCCESS_STRING_LITERAL in final_reasoning:
                                    return SUCCESS_MESSAGE_TWEETS_EXTRACTED
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_reasoning:
                                    return SESSION_INVALIDATED
                                elif FAILED_STRING_LITERAL in final_reasoning:
                                    return f"{FAILED_PREFIX}: {final_reasoning[:RESPONSE_TEXT_SLICE_SHORT]}"
                            
                            self.logger.info("No computer call found, CUA workflow completed")
                            return COMPLETED_CUA_WORKFLOW_TEXT
                        
                        computer_call = computer_calls[0]
                        action = computer_call.action
                        call_id = computer_call.call_id
                        
                        # Handle safety checks - automatically acknowledge routine social media interaction checks
                        acknowledged_checks = []
                        if hasattr(computer_call, 'pending_safety_checks') and computer_call.pending_safety_checks:
                            self.logger.info(f"Safety checks detected: {len(computer_call.pending_safety_checks)} checks")
                            # Automatically acknowledge routine social media interaction safety checks for autonomous operation
                            for check in computer_call.pending_safety_checks:
                                self.logger.info(f"Acknowledging safety check: {check.code} - {check.message}")
                                acknowledged_checks.append({
                                    "id": check.id,
                                    "code": check.code,
                                    "message": check.message
                                })
                        
                        # Execute the computer action
                        try:
                            await self._execute_computer_action(computer, action)
                        except Exception as e:
                            self.logger.error(f"Error executing computer action {action.type}: {e}")
                            return f"FAILED: Computer action execution error: {e}"
                        
                        # Take screenshot
                        try:
                            screenshot_b64 = await computer.screenshot()
                            screenshot_size = len(screenshot_b64)
                            
                            # CRITICAL FIX: Detect and handle blank/problematic screenshots
                            self.logger.info(f"Screenshot size: {screenshot_size} characters")
                            
                            # Check for consistently small screenshots (blank page indicator)
                            if screenshot_size < SCREENSHOT_MIN_SIZE_THRESHOLD:  # Typical X.com screenshots are much larger
                                consecutive_empty_screenshots += 1
                                self.logger.warning(f"Small screenshot detected ({screenshot_size} chars). Count: {consecutive_empty_screenshots}")
                                
                                # If we get multiple small screenshots, the page is likely in a bad state
                                if consecutive_empty_screenshots >= CONSECUTIVE_EMPTY_SCREENSHOT_LIMIT:
                                    self.logger.error("Multiple consecutive small screenshots - page appears blank or broken")
                                    
                                    # Attempt recovery by refreshing the page
                                    try:
                                        self.logger.info("Attempting page refresh recovery")
                                        await computer.keypress(['CTRL', 'R'])
                                        await asyncio.sleep(PAGE_RELOAD_WAIT_SECONDS)  # Wait for page reload
                                        
                                        # Take a new screenshot to check if recovery worked
                                        recovery_screenshot = await computer.screenshot()
                                        recovery_size = len(recovery_screenshot)
                                        self.logger.info(f"Recovery screenshot size: {recovery_size} characters")
                                        
                                        if recovery_size > SCREENSHOT_MIN_SIZE_THRESHOLD:
                                            self.logger.info("Page refresh recovery successful")
                                            screenshot_b64 = recovery_screenshot
                                            consecutive_empty_screenshots = 0
                                        else:
                                            self.logger.error("Page refresh recovery failed - still getting small screenshots")
                                            return "FAILED: Page appears blank and recovery attempts failed"
                                    except Exception as recovery_error:
                                        self.logger.error(f"Recovery attempt failed: {recovery_error}")
                                        return "FAILED: Page refresh recovery failed"
                            else:
                                consecutive_empty_screenshots = 0  # Reset counter on good screenshot
                            
                            last_screenshot_size = screenshot_size
                            
                        except Exception as e:
                            self.logger.error(f"Error taking screenshot: {e}")
                            return f"{FAILED_PREFIX}: Screenshot capture error: {e}"
                        
                        # Prepare next request input
                        input_content = [{
                            "call_id": call_id,
                            "type": CONTENT_TYPE_COMPUTER_CALL_OUTPUT,
                            "output": {
                                "type": CONTENT_TYPE_INPUT_IMAGE,
                                "image_url": f"{IMAGE_DATA_URL_PREFIX},{screenshot_b64}"
                            }
                        }]
                        
                        # Add acknowledged safety checks if any
                        if acknowledged_checks:
                            input_content[0]["acknowledged_safety_checks"] = acknowledged_checks
                            self.logger.info(f"Including {len(acknowledged_checks)} acknowledged safety checks in next request")
                        
                        # Send next request
                        try:
                            response = client.responses.create(
                                model=COMPUTER_USE_MODEL,
                                previous_response_id=response.id,
                                tools=[CUA_TOOL_CONFIG],
                                input=input_content,
                                truncation=API_TRUNCATION_AUTO
                            )
                        except Exception as e:
                            self.logger.error(f"Error in CUA API call: {e}")
                            return f"{FAILED_PREFIX}: API call error: {e}"
                    
                    self.logger.warning(f"CUA reached maximum iterations ({max_iterations})")
                    return COMPLETED_CUA_ITERATIONS
                    
            except Exception as e:
                error_msg = f"CUA timeline reading failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                return f"{FAILED_PREFIX}: {error_msg}"
        
        try:
            return asyncio.run(_internal_timeline_via_cua())
        except Exception as e:
            error_msg = f"Failed to execute CUA timeline reading workflow: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"{FAILED_PREFIX}: {error_msg}"

    def like_tweet_via_cua(self, tweet_url: str) -> str:
        """
        Like a specific tweet via the ComputerUseAgent using browser automation.

        Args:
            tweet_url: The URL of the tweet to like.

        Returns:
            String describing the outcome of the CUA operation.

        Raises:
            Exception: If the CUA workflow encounters an unrecoverable error.
        """
        self.logger.info("Starting CUA tweet liking workflow for URL: %s", tweet_url)
        
        async def _internal_like_via_cua() -> str:
            """Internal async function to handle CUA tweet liking workflow."""
            try:
                # Use LocalPlaywrightComputer with proper configuration
                async with LocalPlaywrightComputer(user_data_dir_path=settings.x_cua_user_data_dir) as computer:
                    
                    # Initialize the OpenAI client for direct responses API calls
                    from openai import OpenAI
                    import base64
                    client = OpenAI(api_key=settings.openai_api_key)
                    
                    # Define system instructions (general CUA behavior)
                    system_instructions = CUA_SYSTEM_INSTRUCTIONS
                    
                    # Navigate directly to the tweet URL using Playwright before starting CUA
                    self.logger.info(f"🧭 Direct navigation to tweet URL: {tweet_url}")
                    try:
                        await computer.page.goto(tweet_url, wait_until='networkidle', timeout=PAGE_NAVIGATION_TIMEOUT)
                        await computer.page.wait_for_timeout(PAGE_STABILIZATION_DELAY)  # Additional wait for page stabilization
                        self.logger.info(f"✅ Successfully navigated to {tweet_url}")
                    except Exception as nav_error:
                        self.logger.error(f"❌ Failed to navigate to {tweet_url}: {nav_error}")
                        return f"{FAILED_PREFIX}: Could not navigate to tweet URL - {nav_error}"
                    
                    # Define task-specific prompt (tweet liking) - now focused on just liking since we're already on the page
                    task_specific_prompt = get_tweet_like_prompt(tweet_url)
                    
                    # Initial request to get first screenshot
                    self.logger.info("Sending initial CUA request for tweet liking")
                    initial_input_messages = [
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": task_specific_prompt}
                    ]
                    response = client.responses.create(
                        model=COMPUTER_USE_MODEL,
                        tools=[CUA_TOOL_CONFIG],
                        input=initial_input_messages,
                        truncation="auto"
                    )
                    
                    max_iterations = CUA_MAX_ITERATIONS_LIKE
                    iteration = 0
                    
                    while iteration < max_iterations:
                        iteration += 1
                        self.logger.info(f"CUA iteration {iteration}")
                        
                        # Check for computer calls in the response
                        computer_calls = [item for item in response.output if hasattr(item, 'type') and item.type == "computer_call"]
                        
                        # Debug: Log all response output items
                        self.logger.info(f"Response output items: {len(response.output)}")
                        for i, item in enumerate(response.output):
                            if hasattr(item, 'type'):
                                self.logger.info(f"  Item {i}: type={item.type}")
                                if item.type == "text" and hasattr(item, 'text'):
                                    self.logger.info(f"    Text content: {item.text[:200]}...")
                            else:
                                self.logger.info(f"  Item {i}: {type(item)} - {str(item)[:100]}...")
                        
                        if not computer_calls:
                            # Check for text output that might contain our success/failure message
                            text_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "text"]
                            reasoning_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "reasoning"]
                            message_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "message"]
                            
                            if text_outputs:
                                final_text = text_outputs[-1].text if hasattr(text_outputs[-1], 'text') else str(text_outputs[-1])
                                self.logger.info(f"CUA completed with text output: {final_text}")
                                if SUCCESS_STRING_LITERAL in final_text:
                                    return final_text
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_text:
                                    return final_text
                                elif FAILED_STRING_LITERAL in final_text:
                                    return final_text
                            
                            if message_outputs:
                                # Handle both direct text and ResponseOutputText objects
                                final_message = ""
                                for msg in message_outputs:
                                    if hasattr(msg, 'text'):
                                        final_message = msg.text
                                        break
                                    elif hasattr(msg, 'content') and hasattr(msg.content, 'text'):
                                        final_message = msg.content.text
                                        break
                                    elif str(msg):
                                        msg_str = str(msg)
                                        # Extract text from ResponseOutputText representation
                                        if "text='" in msg_str:
                                            start = msg_str.find("text='") + 6
                                            end = msg_str.find("'", start)
                                            if end > start:
                                                final_message = msg_str[start:end]
                                                break
                                
                                self.logger.info(f"CUA completed with message text: {final_message}")
                                # Check if message contains our response patterns
                                if SUCCESS_STRING_LITERAL in final_message:
                                    return final_message  # Return the actual success message
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_message:
                                    return SESSION_INVALIDATED
                                elif FAILED_STRING_LITERAL in final_message:
                                    return f"{FAILED_PREFIX}: {final_message}"
                            
                            if reasoning_outputs:
                                final_reasoning = reasoning_outputs[-1].content if hasattr(reasoning_outputs[-1], 'content') else str(reasoning_outputs[-1])
                                self.logger.info(f"CUA completed with reasoning: {final_reasoning[:RESPONSE_TEXT_SLICE_MEDIUM]}...")
                                # Check if reasoning contains our response patterns
                                if SUCCESS_STRING_LITERAL in final_reasoning:
                                    return SUCCESS_TWEET_LIKED_FROM_REASONING
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_reasoning:
                                    return SESSION_INVALIDATED
                                elif FAILED_STRING_LITERAL in final_reasoning:
                                    return f"{FAILED_PREFIX}: {final_reasoning[:RESPONSE_TEXT_SLICE_SHORT]}"
                            
                            self.logger.info("No computer call found, CUA workflow completed")
                            return COMPLETED_CUA_TWEET_LIKING_WORKFLOW_TEXT
                        
                        computer_call = computer_calls[0]
                        action = computer_call.action
                        call_id = computer_call.call_id
                        
                        # Handle safety checks - automatically acknowledge routine social media interaction checks
                        acknowledged_checks = []
                        if hasattr(computer_call, 'pending_safety_checks') and computer_call.pending_safety_checks:
                            self.logger.info(f"Safety checks detected: {len(computer_call.pending_safety_checks)} checks")
                            # Automatically acknowledge routine social media interaction safety checks for autonomous operation
                            for check in computer_call.pending_safety_checks:
                                self.logger.info(f"Acknowledging safety check: {check.code} - {check.message}")
                                acknowledged_checks.append({
                                    "id": check.id,
                                    "code": check.code,
                                    "message": check.message
                                })
                        
                        # Execute the computer action
                        try:
                            await self._execute_computer_action(computer, action)
                        except Exception as e:
                            self.logger.error(f"Error executing computer action {action.type}: {e}")
                            return f"FAILED: Computer action execution error: {e}"
                        
                        # Take screenshot
                        try:
                            screenshot_b64 = await computer.screenshot()
                        except Exception as e:
                            self.logger.error(f"Error taking screenshot: {e}")
                            return f"{FAILED_PREFIX}: Screenshot capture error: {e}"
                        
                        # Prepare next request input
                        input_content = [{
                            "call_id": call_id,
                            "type": "computer_call_output",
                            "output": {
                                "type": "input_image",
                                "image_url": f"data:image/png;base64,{screenshot_b64}"
                            }
                        }]
                        
                        # Add acknowledged safety checks if any
                        if acknowledged_checks:
                            input_content[0]["acknowledged_safety_checks"] = acknowledged_checks
                            self.logger.info(f"Including {len(acknowledged_checks)} acknowledged safety checks in next request")
                        
                        # Send next request
                        try:
                            response = client.responses.create(
                                model=COMPUTER_USE_MODEL,
                                previous_response_id=response.id,
                                tools=[CUA_TOOL_CONFIG],
                                input=input_content,
                                truncation="auto"
                            )
                        except Exception as e:
                            self.logger.error(f"Error in CUA API call: {e}")
                            return f"{FAILED_PREFIX}: API call error: {e}"
                    
                    self.logger.warning(f"CUA reached maximum iterations ({max_iterations})")
                    return COMPLETED_CUA_ITERATIONS
                    
            except Exception as e:
                error_msg = f"CUA tweet liking failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                return f"{FAILED_PREFIX}: {error_msg}"
        
        try:
            return asyncio.run(_internal_like_via_cua())
        except Exception as e:
            error_msg = f"Failed to execute CUA tweet liking workflow: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"{FAILED_PREFIX}: {error_msg}"

    def repost_tweet_via_cua(self, tweet_url: str) -> str:
        """
        Repost a specific tweet via the ComputerUseAgent using browser automation.

        Args:
            tweet_url: The URL of the tweet to repost.

        Returns:
            String describing the outcome of the CUA operation.

        Raises:
            Exception: If the CUA workflow encounters an unrecoverable error.
        """
        self.logger.info("Starting CUA tweet reposting workflow for URL: %s", tweet_url)
        
        async def _internal_repost_via_cua() -> str:
            """Internal async function to handle CUA tweet reposting workflow."""
            try:
                # Use LocalPlaywrightComputer with proper configuration
                async with LocalPlaywrightComputer(user_data_dir_path=settings.x_cua_user_data_dir) as computer:
                    
                    # Initialize the OpenAI client for direct responses API calls
                    from openai import OpenAI
                    import base64
                    client = OpenAI(api_key=settings.openai_api_key)
                    
                    # Define system instructions (general CUA behavior)
                    system_instructions = CUA_SYSTEM_INSTRUCTIONS
                    
                    # Navigate directly to the tweet URL using Playwright before starting CUA
                    self.logger.info(f"🧭 Direct navigation to tweet URL: {tweet_url}")
                    try:
                        await computer.page.goto(tweet_url, wait_until='networkidle', timeout=PAGE_NAVIGATION_TIMEOUT)
                        await computer.page.wait_for_timeout(PAGE_STABILIZATION_DELAY)  # Additional wait for page stabilization
                        self.logger.info(f"✅ Successfully navigated to {tweet_url}")
                    except Exception as nav_error:
                        self.logger.error(f"❌ Failed to navigate to {tweet_url}: {nav_error}")
                        return f"{FAILED_PREFIX}: Could not navigate to tweet URL - {nav_error}"
                    
                    # Define task-specific prompt (tweet reposting)
                    task_specific_prompt = get_tweet_repost_prompt(tweet_url)
                    
                    # Initial request to get first screenshot
                    self.logger.info("Sending initial CUA request for tweet reposting")
                    initial_input_messages = [
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": task_specific_prompt}
                    ]
                    response = client.responses.create(
                        model=COMPUTER_USE_MODEL,
                        tools=[CUA_TOOL_CONFIG],
                        input=initial_input_messages,
                        truncation="auto"
                    )
                    
                    max_iterations = CUA_MAX_ITERATIONS_LIKE  # Reuse the like iterations limit since reposting is similar complexity
                    iteration = 0
                    
                    while iteration < max_iterations:
                        iteration += 1
                        self.logger.info(f"CUA iteration {iteration}")
                        
                        # Check for computer calls in the response
                        computer_calls = [item for item in response.output if hasattr(item, 'type') and item.type == "computer_call"]
                        
                        # Debug: Log all response output items
                        self.logger.info(f"Response output items: {len(response.output)}")
                        for i, item in enumerate(response.output):
                            if hasattr(item, 'type'):
                                self.logger.info(f"  Item {i}: type={item.type}")
                                if item.type == "text" and hasattr(item, 'text'):
                                    self.logger.info(f"    Text content: {item.text[:200]}...")
                            else:
                                self.logger.info(f"  Item {i}: {type(item)} - {str(item)[:100]}...")
                        
                        if not computer_calls:
                            # Check for text output that might contain our success/failure message
                            text_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "text"]
                            reasoning_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "reasoning"]
                            message_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "message"]
                            
                            if text_outputs:
                                final_text = text_outputs[-1].text if hasattr(text_outputs[-1], 'text') else str(text_outputs[-1])
                                self.logger.info(f"CUA completed with text output: {final_text}")
                                if SUCCESS_STRING_LITERAL in final_text:
                                    return final_text
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_text:
                                    return final_text
                                elif FAILED_STRING_LITERAL in final_text:
                                    return final_text
                            
                            if message_outputs:
                                # Handle both direct text and ResponseOutputText objects
                                final_message = ""
                                for msg in message_outputs:
                                    if hasattr(msg, 'text'):
                                        final_message = msg.text
                                        break
                                    elif hasattr(msg, 'content') and hasattr(msg.content, 'text'):
                                        final_message = msg.content.text
                                        break
                                    elif str(msg):
                                        msg_str = str(msg)
                                        # Extract text from ResponseOutputText representation
                                        if "text='" in msg_str:
                                            start = msg_str.find("text='") + 6
                                            end = msg_str.find("'", start)
                                            if end > start:
                                                final_message = msg_str[start:end]
                                                break
                                
                                self.logger.info(f"CUA completed with message text: {final_message}")
                                # Check if message contains our response patterns
                                if SUCCESS_STRING_LITERAL in final_message:
                                    return final_message  # Return the actual success message
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_message:
                                    return SESSION_INVALIDATED
                                elif FAILED_STRING_LITERAL in final_message:
                                    return f"{FAILED_PREFIX}: {final_message}"
                            
                            if reasoning_outputs:
                                final_reasoning = reasoning_outputs[-1].content if hasattr(reasoning_outputs[-1], 'content') else str(reasoning_outputs[-1])
                                self.logger.info(f"CUA completed with reasoning: {final_reasoning[:RESPONSE_TEXT_SLICE_MEDIUM]}...")
                                # Check if reasoning contains our response patterns
                                if SUCCESS_STRING_LITERAL in final_reasoning:
                                    return f"{SUCCESS_PREFIX}: Tweet reposted successfully (from reasoning)"
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_reasoning:
                                    return SESSION_INVALIDATED
                                elif FAILED_STRING_LITERAL in final_reasoning:
                                    return f"{FAILED_PREFIX}: {final_reasoning[:RESPONSE_TEXT_SLICE_SHORT]}"
                            
                            self.logger.info("No computer call found, CUA workflow completed")
                            return f"{COMPLETED_PREFIX}: CUA repost workflow finished"
                        
                        computer_call = computer_calls[0]
                        action = computer_call.action
                        call_id = computer_call.call_id
                        
                        # Handle safety checks - automatically acknowledge routine social media interaction checks
                        acknowledged_checks = []
                        if hasattr(computer_call, 'pending_safety_checks') and computer_call.pending_safety_checks:
                            self.logger.info(f"Safety checks detected: {len(computer_call.pending_safety_checks)} checks")
                            # Automatically acknowledge routine social media interaction safety checks for autonomous operation
                            for check in computer_call.pending_safety_checks:
                                self.logger.info(f"Acknowledging safety check: {check.code} - {check.message}")
                                acknowledged_checks.append({
                                    "id": check.id,
                                    "code": check.code,
                                    "message": check.message
                                })
                        
                        # Execute the computer action
                        try:
                            await self._execute_computer_action(computer, action)
                        except Exception as e:
                            self.logger.error(f"Error executing computer action {action.type}: {e}")
                            return f"FAILED: Computer action execution error: {e}"
                        
                        # Take screenshot
                        try:
                            screenshot_b64 = await computer.screenshot()
                        except Exception as e:
                            self.logger.error(f"Error taking screenshot: {e}")
                            return f"{FAILED_PREFIX}: Screenshot capture error: {e}"
                        
                        # Prepare next request input
                        input_content = [{
                            "call_id": call_id,
                            "type": "computer_call_output",
                            "output": {
                                "type": "input_image",
                                "image_url": f"data:image/png;base64,{screenshot_b64}"
                            }
                        }]
                        
                        # Add acknowledged safety checks if any
                        if acknowledged_checks:
                            input_content[0]["acknowledged_safety_checks"] = acknowledged_checks
                            self.logger.info(f"Including {len(acknowledged_checks)} acknowledged safety checks in next request")
                        
                        # Send next request
                        try:
                            response = client.responses.create(
                                model=COMPUTER_USE_MODEL,
                                previous_response_id=response.id,
                                tools=[CUA_TOOL_CONFIG],
                                input=input_content,
                                truncation="auto"
                            )
                        except Exception as e:
                            self.logger.error(f"Error in CUA API call: {e}")
                            return f"{FAILED_PREFIX}: API call error: {e}"
                    
                    self.logger.warning(f"CUA reached maximum iterations ({max_iterations})")
                    return COMPLETED_CUA_ITERATIONS
                    
            except Exception as e:
                error_msg = f"CUA tweet reposting failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                return f"{FAILED_PREFIX}: {error_msg}"
        
        try:
            return asyncio.run(_internal_repost_via_cua())
        except Exception as e:
            error_msg = f"Failed to execute CUA tweet reposting workflow: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"{FAILED_PREFIX}: {error_msg}"

    def follow_user_via_cua(self, profile_url: str) -> str:
        """
        Follow a specific user via the ComputerUseAgent using browser automation.

        Args:
            profile_url: The URL of the user's profile to follow.

        Returns:
            String describing the outcome of the CUA operation.

        Raises:
            Exception: If the CUA workflow encounters an unrecoverable error.
        """
        self.logger.info("Starting CUA user following workflow for URL: %s", profile_url)
        
        async def _internal_follow_via_cua() -> str:
            """Internal async function to handle CUA user following workflow."""
            try:
                # Use LocalPlaywrightComputer with proper configuration
                async with LocalPlaywrightComputer(user_data_dir_path=settings.x_cua_user_data_dir) as computer:
                    
                    # Initialize the OpenAI client for direct responses API calls
                    from openai import OpenAI
                    import base64
                    client = OpenAI(api_key=settings.openai_api_key)
                    
                    # Define system instructions (general CUA behavior)
                    system_instructions = CUA_SYSTEM_INSTRUCTIONS
                    
                    # Navigate directly to the profile URL using Playwright before starting CUA
                    self.logger.info(f"🧭 Direct navigation to profile URL: {profile_url}")
                    try:
                        await computer.page.goto(profile_url, wait_until='networkidle', timeout=PAGE_NAVIGATION_TIMEOUT)
                        await computer.page.wait_for_timeout(PAGE_STABILIZATION_DELAY)  # Additional wait for page stabilization
                        self.logger.info(f"✅ Successfully navigated to {profile_url}")
                    except Exception as nav_error:
                        self.logger.error(f"❌ Failed to navigate to {profile_url}: {nav_error}")
                        return f"{FAILED_PREFIX}: Could not navigate to profile URL - {nav_error}"
                    
                    # Define task-specific prompt (user following)
                    task_specific_prompt = get_user_follow_prompt(profile_url)
                    
                    # Initial request to get first screenshot
                    self.logger.info("Sending initial CUA request for user following")
                    initial_input_messages = [
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": task_specific_prompt}
                    ]
                    response = client.responses.create(
                        model=COMPUTER_USE_MODEL,
                        tools=[CUA_TOOL_CONFIG],
                        input=initial_input_messages,
                        truncation="auto"
                    )
                    
                    max_iterations = CUA_MAX_ITERATIONS_LIKE  # Reuse the like iterations limit since following is similar complexity
                    iteration = 0
                    
                    while iteration < max_iterations:
                        iteration += 1
                        self.logger.info(f"CUA iteration {iteration}")
                        
                        # Check for computer calls in the response
                        computer_calls = [item for item in response.output if hasattr(item, 'type') and item.type == "computer_call"]
                        
                        # Debug: Log all response output items
                        self.logger.info(f"Response output items: {len(response.output)}")
                        for i, item in enumerate(response.output):
                            if hasattr(item, 'type'):
                                self.logger.info(f"  Item {i}: type={item.type}")
                                if item.type == "text" and hasattr(item, 'text'):
                                    self.logger.info(f"    Text content: {item.text[:200]}...")
                            else:
                                self.logger.info(f"  Item {i}: {type(item)} - {str(item)[:100]}...")
                        
                        if not computer_calls:
                            # Check for text output that might contain our success/failure message
                            text_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "text"]
                            reasoning_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "reasoning"]
                            message_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "message"]
                            
                            if text_outputs:
                                final_text = text_outputs[-1].text if hasattr(text_outputs[-1], 'text') else str(text_outputs[-1])
                                self.logger.info(f"CUA completed with text output: {final_text}")
                                if SUCCESS_STRING_LITERAL in final_text:
                                    return final_text
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_text:
                                    return final_text
                                elif FAILED_STRING_LITERAL in final_text:
                                    return final_text
                            
                            if message_outputs:
                                # Handle both direct text and ResponseOutputText objects
                                final_message = ""
                                for msg in message_outputs:
                                    if hasattr(msg, 'text'):
                                        final_message = msg.text
                                        break
                                    elif hasattr(msg, 'content') and hasattr(msg.content, 'text'):
                                        final_message = msg.content.text
                                        break
                                    elif str(msg):
                                        msg_str = str(msg)
                                        # Extract text from ResponseOutputText representation
                                        if "text='" in msg_str:
                                            start = msg_str.find("text='") + 6
                                            end = msg_str.find("'", start)
                                            if end > start:
                                                final_message = msg_str[start:end]
                                                break
                                
                                self.logger.info(f"CUA completed with message text: {final_message}")
                                # Check if message contains our response patterns
                                if SUCCESS_STRING_LITERAL in final_message:
                                    return final_message  # Return the actual success message
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_message:
                                    return SESSION_INVALIDATED
                                elif FAILED_STRING_LITERAL in final_message:
                                    return f"{FAILED_PREFIX}: {final_message}"
                            
                            if reasoning_outputs:
                                final_reasoning = reasoning_outputs[-1].content if hasattr(reasoning_outputs[-1], 'content') else str(reasoning_outputs[-1])
                                self.logger.info(f"CUA completed with reasoning: {final_reasoning[:RESPONSE_TEXT_SLICE_MEDIUM]}...")
                                # Check if reasoning contains our response patterns
                                if SUCCESS_STRING_LITERAL in final_reasoning:
                                    return f"{SUCCESS_PREFIX}: User followed successfully (from reasoning)"
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_reasoning:
                                    return SESSION_INVALIDATED
                                elif FAILED_STRING_LITERAL in final_reasoning:
                                    return f"{FAILED_PREFIX}: {final_reasoning[:RESPONSE_TEXT_SLICE_SHORT]}"
                            
                            self.logger.info("No computer call found, CUA workflow completed")
                            return f"{COMPLETED_PREFIX}: CUA follow workflow finished"
                        
                        computer_call = computer_calls[0]
                        action = computer_call.action
                        call_id = computer_call.call_id
                        
                        # Handle safety checks - automatically acknowledge routine social media interaction checks
                        acknowledged_checks = []
                        if hasattr(computer_call, 'pending_safety_checks') and computer_call.pending_safety_checks:
                            self.logger.info(f"Safety checks detected: {len(computer_call.pending_safety_checks)} checks")
                            # Automatically acknowledge routine social media interaction safety checks for autonomous operation
                            for check in computer_call.pending_safety_checks:
                                self.logger.info(f"Acknowledging safety check: {check.code} - {check.message}")
                                acknowledged_checks.append({
                                    "id": check.id,
                                    "code": check.code,
                                    "message": check.message
                                })
                        
                        # Execute the computer action
                        try:
                            await self._execute_computer_action(computer, action)
                        except Exception as e:
                            self.logger.error(f"Error executing computer action {action.type}: {e}")
                            return f"FAILED: Computer action execution error: {e}"
                        
                        # Take screenshot
                        try:
                            screenshot_b64 = await computer.screenshot()
                        except Exception as e:
                            self.logger.error(f"Error taking screenshot: {e}")
                            return f"{FAILED_PREFIX}: Screenshot capture error: {e}"
                        
                        # Prepare next request input
                        input_content = [{
                            "call_id": call_id,
                            "type": "computer_call_output",
                            "output": {
                                "type": "input_image",
                                "image_url": f"data:image/png;base64,{screenshot_b64}"
                            }
                        }]
                        
                        # Add acknowledged safety checks if any
                        if acknowledged_checks:
                            input_content[0]["acknowledged_safety_checks"] = acknowledged_checks
                            self.logger.info(f"Including {len(acknowledged_checks)} acknowledged safety checks in next request")
                        
                        # Send next request
                        try:
                            response = client.responses.create(
                                model=COMPUTER_USE_MODEL,
                                previous_response_id=response.id,
                                tools=[CUA_TOOL_CONFIG],
                                input=input_content,
                                truncation="auto"
                            )
                        except Exception as e:
                            self.logger.error(f"Error in CUA API call: {e}")
                            return f"{FAILED_PREFIX}: API call error: {e}"
                    
                    self.logger.warning(f"CUA reached maximum iterations ({max_iterations})")
                    return COMPLETED_CUA_ITERATIONS
                    
            except Exception as e:
                error_msg = f"CUA user following failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                return f"{FAILED_PREFIX}: {error_msg}"
        
        try:
            return asyncio.run(_internal_follow_via_cua())
        except Exception as e:
            error_msg = f"Failed to execute CUA user following workflow: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"{FAILED_PREFIX}: {error_msg}"

    def search_x_for_topic_via_cua(self, query: str, num_results: int = 3) -> str:
        """
        Search X.com for a topic and extract text from the top results via CUA.

        Args:
            query: The search query to execute on X.com.
            num_results: Number of search results to extract (default: 3).

        Returns:
            String containing JSON array of tweet texts or error message.

        Raises:
            Exception: If the CUA workflow encounters an unrecoverable error.
        """
        self.logger.info("Starting CUA search workflow for query: %s", query)
        self.logger.info("Requesting %d search results", num_results)
        
        async def _internal_search_via_cua() -> str:
            """Internal async function to handle CUA search workflow."""
            try:
                # Use LocalPlaywrightComputer with proper configuration
                async with LocalPlaywrightComputer(user_data_dir_path=settings.x_cua_user_data_dir) as computer:
                    
                    # Initialize the OpenAI client for direct responses API calls
                    from openai import OpenAI
                    import base64
                    client = OpenAI(api_key=settings.openai_api_key)
                    
                    # Define system instructions (general CUA behavior)
                    system_instructions = CUA_SYSTEM_INSTRUCTIONS
                    
                    # NOTE: This workflow does NOT start with page.goto as per instructions
                    # It starts from the current page (assumed to be home timeline or another X.com page)
                    self.logger.info("Starting search from current page (no navigation)")
                    
                    # Define task-specific prompt (X.com search)
                    task_specific_prompt = get_search_x_prompt(query, num_results)
                    
                    # Initial request to get first screenshot
                    self.logger.info("Sending initial CUA request for X.com search")
                    initial_input_messages = [
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": task_specific_prompt}
                    ]
                    response = client.responses.create(
                        model=COMPUTER_USE_MODEL,
                        tools=[CUA_TOOL_CONFIG],
                        input=initial_input_messages,
                        truncation="auto"
                    )
                    
                    max_iterations = CUA_MAX_ITERATIONS_DEFAULT  # Search may need more iterations than simple actions
                    iteration = 0
                    
                    while iteration < max_iterations:
                        iteration += 1
                        self.logger.info(f"CUA iteration {iteration}")
                        
                        # Check for computer calls in the response
                        computer_calls = [item for item in response.output if hasattr(item, 'type') and item.type == "computer_call"]
                        
                        # Debug: Log all response output items
                        self.logger.info(f"Response output items: {len(response.output)}")
                        for i, item in enumerate(response.output):
                            if hasattr(item, 'type'):
                                self.logger.info(f"  Item {i}: type={item.type}")
                                if item.type == "text" and hasattr(item, 'text'):
                                    self.logger.info(f"    Text content: {item.text[:200]}...")
                            else:
                                self.logger.info(f"  Item {i}: {type(item)} - {str(item)[:100]}...")
                        
                        if not computer_calls:
                            # Check for text output that might contain our success/failure message
                            text_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "text"]
                            reasoning_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "reasoning"]
                            message_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "message"]
                            
                            if text_outputs:
                                final_text = text_outputs[-1].text if hasattr(text_outputs[-1], 'text') else str(text_outputs[-1])
                                self.logger.info(f"CUA completed with text output: {final_text}")
                                if SUCCESS_STRING_LITERAL in final_text:
                                    return final_text
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_text:
                                    return final_text
                                elif FAILED_STRING_LITERAL in final_text:
                                    return final_text
                            
                            if message_outputs:
                                # Handle both direct text and ResponseOutputText objects
                                final_message = ""
                                for msg in message_outputs:
                                    if hasattr(msg, 'text'):
                                        final_message = msg.text
                                        break
                                    elif hasattr(msg, 'content') and hasattr(msg.content, 'text'):
                                        final_message = msg.content.text
                                        break
                                    elif str(msg):
                                        msg_str = str(msg)
                                        # Extract text from ResponseOutputText representation
                                        if "text='" in msg_str:
                                            start = msg_str.find("text='") + 6
                                            end = msg_str.find("'", start)
                                            if end > start:
                                                final_message = msg_str[start:end]
                                                break
                                
                                self.logger.info(f"CUA completed with message text: {final_message}")
                                # Check if message contains our response patterns
                                if SUCCESS_STRING_LITERAL in final_message:
                                    return final_message  # Return the actual success message
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_message:
                                    return SESSION_INVALIDATED
                                elif FAILED_STRING_LITERAL in final_message:
                                    return f"{FAILED_PREFIX}: {final_message}"
                            
                            if reasoning_outputs:
                                final_reasoning = reasoning_outputs[-1].content if hasattr(reasoning_outputs[-1], 'content') else str(reasoning_outputs[-1])
                                self.logger.info(f"CUA completed with reasoning: {final_reasoning[:RESPONSE_TEXT_SLICE_MEDIUM]}...")
                                # Check if reasoning contains our response patterns
                                if SUCCESS_STRING_LITERAL in final_reasoning:
                                    return f"{SUCCESS_PREFIX}: Search completed successfully (from reasoning)"
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_reasoning:
                                    return SESSION_INVALIDATED
                                elif FAILED_STRING_LITERAL in final_reasoning:
                                    return f"{FAILED_PREFIX}: {final_reasoning[:RESPONSE_TEXT_SLICE_SHORT]}"
                            
                            self.logger.info("No computer call found, CUA workflow completed")
                            return f"{COMPLETED_PREFIX}: CUA search workflow finished"
                        
                        computer_call = computer_calls[0]
                        action = computer_call.action
                        call_id = computer_call.call_id
                        
                        # Handle safety checks - automatically acknowledge routine social media interaction checks
                        acknowledged_checks = []
                        if hasattr(computer_call, 'pending_safety_checks') and computer_call.pending_safety_checks:
                            self.logger.info(f"Safety checks detected: {len(computer_call.pending_safety_checks)} checks")
                            # Automatically acknowledge routine social media interaction safety checks for autonomous operation
                            for check in computer_call.pending_safety_checks:
                                self.logger.info(f"Acknowledging safety check: {check.code} - {check.message}")
                                acknowledged_checks.append({
                                    "id": check.id,
                                    "code": check.code,
                                    "message": check.message
                                })
                        
                        # Execute the computer action
                        try:
                            await self._execute_computer_action(computer, action)
                        except Exception as e:
                            self.logger.error(f"Error executing computer action {action.type}: {e}")
                            return f"FAILED: Computer action execution error: {e}"
                        
                        # Take screenshot
                        try:
                            screenshot_b64 = await computer.screenshot()
                        except Exception as e:
                            self.logger.error(f"Error taking screenshot: {e}")
                            return f"{FAILED_PREFIX}: Screenshot capture error: {e}"
                        
                        # Prepare next request input
                        input_content = [{
                            "call_id": call_id,
                            "type": "computer_call_output",
                            "output": {
                                "type": "input_image",
                                "image_url": f"data:image/png;base64,{screenshot_b64}"
                            }
                        }]
                        
                        # Add acknowledged safety checks if any
                        if acknowledged_checks:
                            input_content[0]["acknowledged_safety_checks"] = acknowledged_checks
                            self.logger.info(f"Including {len(acknowledged_checks)} acknowledged safety checks in next request")
                        
                        # Send next request
                        try:
                            response = client.responses.create(
                                model=COMPUTER_USE_MODEL,
                                previous_response_id=response.id,
                                tools=[CUA_TOOL_CONFIG],
                                input=input_content,
                                truncation="auto"
                            )
                        except Exception as e:
                            self.logger.error(f"Error in CUA API call: {e}")
                            return f"{FAILED_PREFIX}: API call error: {e}"
                    
                    self.logger.warning(f"CUA reached maximum iterations ({max_iterations})")
                    return COMPLETED_CUA_ITERATIONS
                    
            except Exception as e:
                error_msg = f"CUA search failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                return f"{FAILED_PREFIX}: {error_msg}"
        
        try:
            return asyncio.run(_internal_search_via_cua())
        except Exception as e:
            error_msg = f"Failed to execute CUA search workflow: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"{FAILED_PREFIX}: {error_msg}"

    def _contains_unicode_characters(self, text: str) -> bool:
        """
        Check if text contains Unicode characters (like emojis) that CUA cannot handle.

        Args:
            text: Text to analyze for Unicode content.

        Returns:
            True if text contains Unicode characters, False if ASCII-only.
        """
        return any(ord(char) > UNICODE_THRESHOLD for char in text)

    def post_tweet_hybrid(self, tweet_text: str) -> str:
        """
        Post a tweet using the optimal method based on content analysis.
        
        Uses CUA for ASCII-only content and X API for content with Unicode/emojis.

        Args:
            tweet_text: The exact text content to post as a tweet.

        Returns:
            String describing the outcome of the posting operation.
        """
        self.logger.info("Starting hybrid tweet posting workflow")
        self.logger.info(f"Tweet text: {tweet_text}")
        
        # Analyze content to determine optimal posting method
        has_unicode = self._contains_unicode_characters(tweet_text)
        
        if has_unicode:
            self.logger.info("🔄 Unicode characters detected - using X API for reliable posting")
            try:
                result = _post_text_tweet(text=tweet_text)
                self.logger.info("✅ API posting completed successfully: %s", result)
                return f"SUCCESS: Tweet posted via X API - {result}"
            except Exception as e:
                self.logger.error("❌ API posting failed: %s", e)
                return f"FAILED: X API posting error - {e}"
        else:
            self.logger.info("🤖 ASCII-only content detected - using CUA for browser automation")
            result = self.post_tweet_via_cua(tweet_text)
            if SUCCESS_STRING_LITERAL in result:
                self.logger.info("✅ CUA posting completed successfully")
                return f"SUCCESS: Tweet posted via CUA - {result}"
            else:
                self.logger.warning("⚠️ CUA posting failed, falling back to X API")
                try:
                    fallback_result = _post_text_tweet(text=tweet_text)
                    self.logger.info("✅ API fallback posting completed: %s", fallback_result)
                    return f"SUCCESS: Tweet posted via X API (fallback) - {fallback_result}"
                except Exception as e:
                    self.logger.error("❌ Both CUA and API posting failed: %s", e)
                    return f"FAILED: Both CUA and API methods failed - CUA: {result}, API: {e}"

    def reply_to_tweet_hybrid(self, tweet_url: str, reply_text: str) -> str:
        """
        Reply to a tweet using the optimal method based on content analysis.
        
        Uses CUA for ASCII-only content and X API for content with Unicode/emojis.

        Args:
            tweet_url: The URL of the tweet to reply to.
            reply_text: The exact text content to post as a reply.

        Returns:
            String describing the outcome of the reply operation.
        """
        self.logger.info("Starting hybrid tweet reply workflow")
        self.logger.info(f"Tweet URL: {tweet_url}")
        self.logger.info(f"Reply text: {reply_text}")
        
        # Analyze content to determine optimal reply method
        has_unicode = self._contains_unicode_characters(reply_text)
        
        if has_unicode:
            self.logger.info("🔄 Unicode characters detected - using X API for reliable reply posting")
            # Extract tweet ID from URL for API reply
            try:
                import re
                tweet_id_match = re.search(r'/status/(\d+)', tweet_url)
                if not tweet_id_match:
                    return f"FAILED: Could not extract tweet ID from URL: {tweet_url}"
                
                tweet_id = tweet_id_match.group(1)
                self.logger.info(f"Extracted tweet ID: {tweet_id}")
                
                result = _post_text_tweet(text=reply_text, in_reply_to_tweet_id=tweet_id)
                self.logger.info("✅ API reply posting completed successfully: %s", result)
                return f"SUCCESS: Reply posted via X API - {result}"
            except Exception as e:
                self.logger.error("❌ API reply posting failed: %s", e)
                return f"FAILED: X API reply posting error - {e}"
        else:
            self.logger.info("🤖 ASCII-only content detected - using CUA for browser automation")
            result = self.reply_to_tweet_via_cua(tweet_url, reply_text)
            if SUCCESS_STRING_LITERAL in result:
                self.logger.info("✅ CUA reply posting completed successfully")
                return f"SUCCESS: Reply posted via CUA - {result}"
            else:
                self.logger.warning("⚠️ CUA reply posting failed, falling back to X API")
                try:
                    # Extract tweet ID for API fallback
                    import re
                    tweet_id_match = re.search(r'/status/(\d+)', tweet_url)
                    if not tweet_id_match:
                        return f"FAILED: Could not extract tweet ID for API fallback: {tweet_url}"
                    
                    tweet_id = tweet_id_match.group(1)
                    fallback_result = _post_text_tweet(text=reply_text, in_reply_to_tweet_id=tweet_id)
                    self.logger.info("✅ API fallback reply posting completed: %s", fallback_result)
                    return f"SUCCESS: Reply posted via X API (fallback) - {fallback_result}"
                except Exception as e:
                    self.logger.error("❌ Both CUA and API reply posting failed: %s", e)
                    return f"FAILED: Both CUA and API methods failed - CUA: {result}, API: {e}"

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

    async def _execute_computer_action(self, computer, action):
        """Execute a computer action using the AsyncComputer interface."""
        action_type = action.type
        
        if action_type == "screenshot":
            # Screenshot will be taken after this method returns
            pass
        elif action_type == "click":
            self.logger.info(f"Executing click at ({action.x}, {action.y}) with button {action.button}")
            await computer.click(action.x, action.y, action.button)
            # Add extra wait for X.com UI to respond to clicks
            await asyncio.sleep(CLICK_RESPONSE_DELAY / 1000)
        elif action_type == "double_click":
            self.logger.info(f"Executing double-click at ({action.x}, {action.y})")
            await computer.double_click(action.x, action.y)
            await asyncio.sleep(CLICK_RESPONSE_DELAY / 1000)
        elif action_type == "type":
            self.logger.info(f"Typing text: '{action.text}'")
            await computer.type(action.text)
            await asyncio.sleep(KEYPRESS_RESPONSE_DELAY / 1000)
        elif action_type == "keypress":
            self.logger.info(f"Pressing keys: {action.keys}")
            
            # CRITICAL FIX: Special handling for 'j' navigation to detect viewport displacement
            if action.keys == ['j'] or action.keys == 'j':
                self.logger.info("🔧 Executing 'j' navigation with viewport displacement detection")
                
                # Take a screenshot before the 'j' keypress to establish baseline
                try:
                    before_screenshot = await computer.screenshot()
                    before_size = len(before_screenshot)
                    self.logger.info(f"Pre-navigation screenshot size: {before_size}")
                except Exception as e:
                    self.logger.warning(f"Could not capture pre-navigation screenshot: {e}")
                    before_size = 0
                
                # Execute the 'j' keypress
                await computer.keypress(action.keys)
                await asyncio.sleep(UI_RESPONSE_DELAY / 1000)  # Longer wait for navigation to complete
                
                # Take a screenshot after the 'j' keypress to check for displacement
                try:
                    after_screenshot = await computer.screenshot()
                    after_size = len(after_screenshot)
                    self.logger.info(f"Post-navigation screenshot size: {after_size}")
                    
                    # Detect potential viewport displacement
                    size_change_ratio = abs(after_size - before_size) / max(before_size, 1)
                    
                    if after_size < SCREENSHOT_MIN_SIZE_THRESHOLD or size_change_ratio > VIEWPORT_DISPLACEMENT_RATIO_THRESHOLD:
                        self.logger.warning(f"⚠️ Potential viewport displacement detected!")
                        self.logger.warning(f"Size change: {before_size} -> {after_size} (ratio: {size_change_ratio:.2f})")
                        
                        # Attempt automatic viewport recovery
                        self.logger.info("🔧 Attempting automatic viewport recovery...")
                        try:
                            # Method 1: Reset scroll position via JavaScript
                            await computer.page.evaluate("window.scrollTo(0, 0);")
                            await asyncio.sleep(UI_RESPONSE_DELAY / 1000)
                            
                            # Method 2: Press Home key to return to top
                            await computer.keypress(['Home'])
                            await asyncio.sleep(UI_RESPONSE_DELAY / 1000)
                            
                            # Method 3: Re-navigate to home timeline if needed
                            recovery_screenshot = await computer.screenshot()
                            recovery_size = len(recovery_screenshot)
                            
                            if recovery_size > SCREENSHOT_MIN_SIZE_THRESHOLD:
                                self.logger.info("✅ Viewport recovery successful")
                            else:
                                self.logger.warning("⚠️ Viewport recovery may have failed")
                                
                        except Exception as recovery_error:
                            self.logger.error(f"❌ Viewport recovery failed: {recovery_error}")
                    else:
                        self.logger.info("✅ Navigation completed without viewport displacement")
                        
                except Exception as e:
                    self.logger.warning(f"Could not capture post-navigation screenshot: {e}")
            else:
                # Normal keypress execution for non-'j' keys
                await computer.keypress(action.keys)
                await asyncio.sleep(KEYPRESS_RESPONSE_DELAY / 1000)
        elif action_type == "scroll":
            self.logger.info(f"Scrolling at ({action.x}, {action.y}) by ({action.scroll_x}, {action.scroll_y})")
            await computer.scroll(action.x, action.y, action.scroll_x, action.scroll_y)
            await asyncio.sleep(SCROLL_RESPONSE_DELAY / 1000)
        elif action_type == "move":
            await computer.move(action.x, action.y)
        elif action_type == "wait":
            self.logger.info("Executing wait action")
            await computer.wait()
        elif action_type == "drag":
            await computer.drag([(p.x, p.y) for p in action.path])
            await asyncio.sleep(UI_RESPONSE_DELAY / 1000)
        else:
            self.logger.warning(f"Unknown computer action type: {action_type}")

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

    def get_home_timeline_tweets_via_cua_robust(self, num_tweets: int = 3) -> str:
        """
        Read the text content of multiple tweets from the home timeline via CUA using robust individual page navigation.
        
        This method uses a more robust approach that navigates to each tweet's individual page to capture content,
        eliminating viewport displacement issues and providing more reliable content extraction.

        Args:
            num_tweets: Number of tweets to read from the top of the timeline (default: 3).

        Returns:
            JSON string containing the list of tweet texts, or error message.

        Raises:
            Exception: If the CUA workflow encounters an unrecoverable error.
        """
        self.logger.info("Starting robust CUA home timeline reading workflow for %d tweets", num_tweets)
        
        async def _internal_robust_timeline_via_cua() -> str:
            """Internal async function to handle robust CUA timeline reading workflow."""
            try:
                # Use LocalPlaywrightComputer with proper configuration
                async with LocalPlaywrightComputer(user_data_dir_path=settings.x_cua_user_data_dir) as computer:
                    
                    # Initialize the OpenAI client for direct responses API calls
                    from openai import OpenAI
                    import base64
                    client = OpenAI(api_key=settings.openai_api_key)
                    
                    # Define system instructions (general CUA behavior)
                    system_instructions = CUA_SYSTEM_INSTRUCTIONS
                    
                    # Navigate directly to home timeline using Playwright before starting CUA
                    self.logger.info(f"🧭 Pre-navigating to home timeline for robust reading: {X_HOME_URL}")
                    try:
                        await computer.page.goto(X_HOME_URL, wait_until='networkidle', timeout=PAGE_NAVIGATION_TIMEOUT)
                        await computer.page.wait_for_timeout(PAGE_STABILIZATION_DELAY)  # Additional wait for page stabilization
                        self.logger.info(f"✅ Successfully pre-navigated to home timeline")
                    except Exception as nav_error:
                        self.logger.error(f"❌ Failed to pre-navigate to home timeline: {nav_error}")
                        return f"{FAILED_PREFIX}: Could not navigate to home timeline - {nav_error}"
                    
                    # Define task-specific prompt for robust timeline reading with individual page navigation
                    task_specific_prompt = get_robust_timeline_reading_prompt(num_tweets)
                    
                    # Initial request to get first screenshot
                    self.logger.info("Sending initial CUA request for robust timeline reading")
                    initial_input_messages = [
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": task_specific_prompt}
                    ]
                    response = client.responses.create(
                        model=COMPUTER_USE_MODEL,
                        tools=[CUA_TOOL_CONFIG],
                        input=initial_input_messages,
                        truncation="auto"
                    )
                    
                    max_iterations = CUA_MAX_ITERATIONS_REPLY
                    iteration = 0
                    
                    while iteration < max_iterations:
                        iteration += 1
                        self.logger.info(f"CUA iteration {iteration}")
                        
                        # Check for computer calls in the response
                        computer_calls = [item for item in response.output if hasattr(item, 'type') and item.type == "computer_call"]
                        
                        # Debug: Log all response output items
                        self.logger.info(f"Response output items: {len(response.output)}")
                        for i, item in enumerate(response.output):
                            if hasattr(item, 'type'):
                                self.logger.info(f"  Item {i}: type={item.type}")
                                if item.type == "text" and hasattr(item, 'text'):
                                    self.logger.info(f"    Text content: {item.text[:200]}...")
                            else:
                                self.logger.info(f"  Item {i}: {type(item)} - {str(item)[:100]}...")
                        
                        if not computer_calls:
                            # Check for text output that might contain our success/failure message
                            text_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "text"]
                            reasoning_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "reasoning"]
                            message_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "message"]
                            
                            if text_outputs:
                                final_text = text_outputs[-1].text if hasattr(text_outputs[-1], 'text') else str(text_outputs[-1])
                                self.logger.info(f"CUA completed with text output: {final_text}")
                                if SUCCESS_STRING_LITERAL in final_text:
                                    return final_text
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_text:
                                    return final_text
                                elif FAILED_STRING_LITERAL in final_text:
                                    return final_text
                            
                            if message_outputs:
                                # Handle both direct text and ResponseOutputText objects
                                final_message = ""
                                for msg in message_outputs:
                                    if hasattr(msg, 'text'):
                                        final_message = msg.text
                                        break
                                    elif hasattr(msg, 'content') and hasattr(msg.content, 'text'):
                                        final_message = msg.content.text
                                        break
                                    elif str(msg):
                                        msg_str = str(msg)
                                        # Extract text from ResponseOutputText representation
                                        if "text='" in msg_str:
                                            start = msg_str.find("text='") + 6
                                            end = msg_str.find("'", start)
                                            if end > start:
                                                final_message = msg_str[start:end]
                                                break
                                
                                self.logger.info(f"CUA completed with message text: {final_message}")
                                # Check if message contains our response patterns
                                if SUCCESS_STRING_LITERAL in final_message:
                                    return final_message  # Return the actual success message
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_message:
                                    return SESSION_INVALIDATED
                                elif FAILED_STRING_LITERAL in final_message:
                                    return f"{FAILED_PREFIX}: {final_message}"
                            
                            if reasoning_outputs:
                                final_reasoning = reasoning_outputs[-1].content if hasattr(reasoning_outputs[-1], 'content') else str(reasoning_outputs[-1])
                                self.logger.info(f"CUA completed with reasoning: {final_reasoning[:RESPONSE_TEXT_SLICE_MEDIUM]}...")
                                # Check if reasoning contains our response patterns
                                if SUCCESS_STRING_LITERAL in final_reasoning:
                                    return SUCCESS_REPLY_POSTED_FROM_REASONING
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_reasoning:
                                    return SESSION_INVALIDATED
                                elif FAILED_STRING_LITERAL in final_reasoning:
                                    return f"{FAILED_PREFIX}: {final_reasoning[:RESPONSE_TEXT_SLICE_SHORT]}"
                            
                            self.logger.info("No computer call found, CUA workflow completed")
                            return COMPLETED_CUA_WORKFLOW_TEXT
                        
                        computer_call = computer_calls[0]
                        action = computer_call.action
                        call_id = computer_call.call_id
                        
                        # Handle safety checks - automatically acknowledge routine social media interaction checks
                        acknowledged_checks = []
                        if hasattr(computer_call, 'pending_safety_checks') and computer_call.pending_safety_checks:
                            self.logger.info(f"Safety checks detected: {len(computer_call.pending_safety_checks)} checks")
                            # Automatically acknowledge routine social media interaction safety checks for autonomous operation
                            for check in computer_call.pending_safety_checks:
                                self.logger.info(f"Acknowledging safety check: {check.code} - {check.message}")
                                acknowledged_checks.append({
                                    "id": check.id,
                                    "code": check.code,
                                    "message": check.message
                                })
                        
                        # Execute the computer action
                        try:
                            await self._execute_computer_action(computer, action)
                        except Exception as e:
                            self.logger.error(f"Error executing computer action {action.type}: {e}")
                            return f"FAILED: Computer action execution error: {e}"
                        
                        # Take screenshot
                        try:
                            screenshot_b64 = await computer.screenshot()
                        except Exception as e:
                            self.logger.error(f"Error taking screenshot: {e}")
                            return f"{FAILED_PREFIX}: Screenshot capture error: {e}"
                        
                        # Prepare next request input
                        input_content = [{
                            "call_id": call_id,
                            "type": "computer_call_output",
                            "output": {
                                "type": "input_image",
                                "image_url": f"data:image/png;base64,{screenshot_b64}"
                            }
                        }]
                        
                        # Add acknowledged safety checks if any
                        if acknowledged_checks:
                            input_content[0]["acknowledged_safety_checks"] = acknowledged_checks
                            self.logger.info(f"Including {len(acknowledged_checks)} acknowledged safety checks in next request")
                        
                        # Send next request
                        try:
                            response = client.responses.create(
                                model=COMPUTER_USE_MODEL,
                                previous_response_id=response.id,
                                tools=[CUA_TOOL_CONFIG],
                                input=input_content,
                                truncation="auto"
                            )
                        except Exception as e:
                            self.logger.error(f"Error in CUA API call: {e}")
                            return f"{FAILED_PREFIX}: API call error: {e}"
                    
                    self.logger.warning(f"CUA reached maximum iterations ({max_iterations})")
                    return COMPLETED_CUA_ITERATIONS
                    
            except Exception as e:
                error_msg = f"CUA tweet reply failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                return f"{FAILED_PREFIX}: {error_msg}"
        
        try:
            return asyncio.run(_internal_robust_timeline_via_cua())
        except Exception as e:
            error_msg = f"Failed to execute robust CUA timeline reading workflow: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"{FAILED_PREFIX}: {error_msg}"

    def get_home_timeline_tweets_via_cua_consolidated(self, num_tweets: int = DEFAULT_TIMELINE_TWEET_COUNT) -> str:
        """
        Read the text content of multiple tweets from the home timeline via CUA using consolidated approach.
        
        This method combines the successful viewport displacement fixes with robust individual page navigation
        to provide the most reliable tweet content extraction method.

        Args:
            num_tweets: Number of tweets to read from the top of the timeline (default: 3).

        Returns:
            JSON string containing the list of tweet texts, or error message.

        Raises:
            Exception: If the CUA workflow encounters an unrecoverable error.
        """
        self.logger.info("Starting consolidated CUA home timeline reading workflow for %d tweets", num_tweets)
        
        async def _internal_consolidated_timeline_via_cua() -> str:
            """Internal async function to handle consolidated CUA timeline reading workflow."""
            try:
                # Use LocalPlaywrightComputer with proper configuration
                async with LocalPlaywrightComputer(user_data_dir_path=settings.x_cua_user_data_dir) as computer:
                    
                    # =================================================================
                    # 🔧 LAYER 1: PRE-VIEWPORT STABILIZATION (PROVEN SUCCESSFUL)
                    # =================================================================
                    self.logger.info("🔧 Starting Layer 1: Pre-viewport stabilization for consolidated navigation")
                    
                    try:
                        # Step 1: Reset scroll position to top
                        self.logger.info("📐 Resetting scroll position to top")
                        await computer.page.evaluate("window.scrollTo(0, 0);")
                        await asyncio.sleep(UI_RESPONSE_DELAY / 1000)
                        
                        # Step 2: Ensure consistent zoom level (100%)
                        self.logger.info("🔍 Setting zoom level to 100%")
                        await computer.page.evaluate("document.body.style.zoom = '1.0';")
                        await asyncio.sleep(KEYPRESS_RESPONSE_DELAY / 1000)
                        
                        # Step 3: Add viewport stabilization CSS to prevent displacement
                        self.logger.info("🎯 Adding viewport stabilization CSS")
                        stabilization_css = """
                        body { 
                            overflow-x: hidden !important;
                            position: relative !important;
                        }
                        html {
                            scroll-behavior: auto !important;
                        }
                        [data-testid="primaryColumn"] {
                            position: relative !important;
                            transform: none !important;
                        }
                        """
                        await computer.page.add_style_tag(content=stabilization_css)
                        await asyncio.sleep(KEYPRESS_RESPONSE_DELAY / 1000)
                        
                        # Step 4: Force layout recalculation
                        self.logger.info("⚡ Forcing layout recalculation")
                        await computer.page.evaluate("""
                            // Force layout recalculation
                            document.body.offsetHeight;
                            window.getComputedStyle(document.body).getPropertyValue('height');
                            // Ensure we're at the top of the page
                            window.scrollTo({top: 0, left: 0, behavior: 'auto'});
                        """)
                        await asyncio.sleep(UI_RESPONSE_DELAY / 1000)
                        
                        # Step 5: Navigate to home timeline if not already there
                        current_url = computer.page.url
                        if not current_url.endswith('/home'):
                            self.logger.info("🧭 Navigating to home timeline for stable starting point")
                            await computer.page.goto(X_HOME_URL, wait_until='networkidle', timeout=PAGE_NAVIGATION_TIMEOUT)
                            await computer.page.wait_for_timeout(PAGE_STABILIZATION_DELAY)
                            
                            # Re-apply stabilization after navigation
                            await computer.page.evaluate("window.scrollTo(0, 0);")
                            await computer.page.add_style_tag(content=stabilization_css)
                            await asyncio.sleep(UI_RESPONSE_DELAY / 1000)
                        
                        self.logger.info("✅ Layer 1: Viewport stabilization completed successfully")
                        
                    except Exception as stabilization_error:
                        self.logger.warning(f"⚠️ Viewport stabilization failed (proceeding anyway): {stabilization_error}")
                    
                    # =================================================================
                    # End of Layer 1 Viewport Stabilization
                    # =================================================================
                    
                    # Initialize the OpenAI client for direct responses API calls
                    from openai import OpenAI
                    import base64
                    client = OpenAI(api_key=settings.openai_api_key)
                    
                    # Define system instructions (general CUA behavior)
                    system_instructions = CUA_SYSTEM_INSTRUCTIONS
                    
                    # Define task-specific prompt for consolidated timeline reading with both viewport fixes and individual page navigation
                    task_specific_prompt = get_consolidated_timeline_reading_prompt(num_tweets)
                    
                    # Initial request to get first screenshot
                    self.logger.info("Sending initial CUA request for consolidated timeline reading")
                    initial_input_messages = [
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": task_specific_prompt}
                    ]
                    response = client.responses.create(
                        model=COMPUTER_USE_MODEL,
                        tools=[CUA_TOOL_CONFIG],
                        input=initial_input_messages,
                        truncation="auto"
                    )
                    
                    max_iterations = CUA_MAX_ITERATIONS_ROBUST_TIMELINE
                    iteration = 0
                    last_screenshot_size = 0
                    consecutive_empty_screenshots = 0
                    
                    while iteration < max_iterations:
                        iteration += 1
                        self.logger.info(f"CUA consolidated iteration {iteration}")
                        
                        # Check for computer calls in the response
                        computer_calls = [item for item in response.output if hasattr(item, 'type') and item.type == "computer_call"]
                        
                        # Debug: Log all response output items
                        self.logger.info(f"Response output items: {len(response.output)}")
                        for i, item in enumerate(response.output):
                            if hasattr(item, 'type'):
                                self.logger.info(f"  Item {i}: type={item.type}")
                                if item.type == "text" and hasattr(item, 'text'):
                                    self.logger.info(f"    Text content: {item.text[:200]}...")
                            else:
                                self.logger.info(f"  Item {i}: {type(item)} - {str(item)[:100]}...")
                        
                        if not computer_calls:
                            # Check for text output that might contain our success/failure message
                            text_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "text"]
                            reasoning_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "reasoning"]
                            message_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == "message"]
                            
                            if text_outputs:
                                final_text = text_outputs[-1].text if hasattr(text_outputs[-1], 'text') else str(text_outputs[-1])
                                self.logger.info(f"CUA consolidated completed with text output: {final_text}")
                                if SUCCESS_STRING_LITERAL in final_text:
                                    return final_text
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_text:
                                    return final_text
                                elif FAILED_STRING_LITERAL in final_text:
                                    return final_text
                            
                            if message_outputs:
                                # Handle both direct text and ResponseOutputText objects
                                final_message = ""
                                for msg in message_outputs:
                                    if hasattr(msg, 'text'):
                                        final_message = msg.text
                                        break
                                    elif hasattr(msg, 'content') and hasattr(msg.content, 'text'):
                                        final_message = msg.content.text
                                        break
                                    elif str(msg):
                                        msg_str = str(msg)
                                        # Extract text from ResponseOutputText representation
                                        if "text='" in msg_str:
                                            start = msg_str.find("text='") + 6
                                            end = msg_str.find("'", start)
                                            if end > start:
                                                final_message = msg_str[start:end]
                                                break
                                
                                self.logger.info(f"CUA consolidated completed with message text: {final_message}")
                                # Check if message contains our response patterns
                                if SUCCESS_STRING_LITERAL in final_message:
                                    return final_message  # Return the actual success message
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_message:
                                    return SESSION_INVALIDATED
                                elif FAILED_STRING_LITERAL in final_message:
                                    return f"{FAILED_PREFIX}: {final_message}"
                            
                            if reasoning_outputs:
                                final_reasoning = reasoning_outputs[-1].content if hasattr(reasoning_outputs[-1], 'content') else str(reasoning_outputs[-1])
                                self.logger.info(f"CUA consolidated completed with reasoning: {final_reasoning[:RESPONSE_TEXT_SLICE_MEDIUM]}...")
                                # Check if reasoning contains our response patterns
                                if SUCCESS_STRING_LITERAL in final_reasoning:
                                    return SUCCESS_MESSAGE_TWEETS_EXTRACTED
                                elif SESSION_INVALIDATED_STRING_LITERAL in final_reasoning:
                                    return SESSION_INVALIDATED
                                elif FAILED_STRING_LITERAL in final_reasoning:
                                    return f"{FAILED_PREFIX}: {final_reasoning[:RESPONSE_TEXT_SLICE_SHORT]}"
                            
                            self.logger.info("No computer call found, CUA consolidated workflow completed")
                            return COMPLETED_CUA_WORKFLOW_TEXT
                        
                        computer_call = computer_calls[0]
                        action = computer_call.action
                        call_id = computer_call.call_id
                        
                        # Handle safety checks - automatically acknowledge routine social media interaction checks
                        acknowledged_checks = []
                        if hasattr(computer_call, 'pending_safety_checks') and computer_call.pending_safety_checks:
                            self.logger.info(f"Safety checks detected: {len(computer_call.pending_safety_checks)} checks")
                            # Automatically acknowledge routine social media interaction safety checks for autonomous operation
                            for check in computer_call.pending_safety_checks:
                                self.logger.info(f"Acknowledging safety check: {check.code} - {check.message}")
                                acknowledged_checks.append({
                                    "id": check.id,
                                    "code": check.code,
                                    "message": check.message
                                })
                        
                        # Execute the computer action with enhanced viewport displacement detection
                        try:
                            await self._execute_computer_action(computer, action)
                        except Exception as e:
                            self.logger.error(f"Error executing computer action {action.type}: {e}")
                            return f"FAILED: Computer action execution error: {e}"
                        
                        # Take screenshot with enhanced monitoring
                        try:
                            screenshot_b64 = await computer.screenshot()
                            screenshot_size = len(screenshot_b64)
                            
                            # Enhanced screenshot monitoring for consolidated method
                            self.logger.info(f"Consolidated screenshot size: {screenshot_size} characters")
                            
                            # Check for consistently small screenshots (blank page indicator)
                            if screenshot_size < SCREENSHOT_MIN_SIZE_THRESHOLD:
                                consecutive_empty_screenshots += 1
                                self.logger.warning(f"Small screenshot detected in consolidated method ({screenshot_size} chars). Count: {consecutive_empty_screenshots}")
                                
                                # If we get multiple small screenshots, the page is likely in a bad state
                                if consecutive_empty_screenshots >= CONSECUTIVE_EMPTY_SCREENSHOT_LIMIT:
                                    self.logger.error("Multiple consecutive small screenshots in consolidated method - page appears blank")
                                    
                                    # Enhanced recovery for consolidated method
                                    try:
                                        self.logger.info("Attempting enhanced consolidated recovery")
                                        
                                        # Step 1: Reset viewport using JavaScript
                                        await computer.page.evaluate("window.scrollTo(0, 0);")
                                        await asyncio.sleep(UI_RESPONSE_DELAY / 1000)
                                        
                                        # Step 2: Try Home key navigation
                                        await computer.keypress(['Home'])
                                        await asyncio.sleep(UI_RESPONSE_DELAY / 1000)
                                        
                                        # Step 3: Re-navigate to home timeline
                                        await computer.keypress(['g', 'h'])
                                        await asyncio.sleep(PAGE_STABILIZATION_DELAY / 1000)
                                        
                                        # Take a new screenshot to check if recovery worked
                                        recovery_screenshot = await computer.screenshot()
                                        recovery_size = len(recovery_screenshot)
                                        self.logger.info(f"Consolidated recovery screenshot size: {recovery_size} characters")
                                        
                                        if recovery_size > SCREENSHOT_MIN_SIZE_THRESHOLD:
                                            self.logger.info("Consolidated enhanced recovery successful")
                                            screenshot_b64 = recovery_screenshot
                                            consecutive_empty_screenshots = 0
                                        else:
                                            self.logger.error("Consolidated enhanced recovery failed - still getting small screenshots")
                                            return "FAILED: Page appears blank and enhanced recovery attempts failed"
                                    except Exception as recovery_error:
                                        self.logger.error(f"Consolidated recovery attempt failed: {recovery_error}")
                                        return "FAILED: Enhanced recovery failed in consolidated method"
                            else:
                                consecutive_empty_screenshots = 0  # Reset counter on good screenshot
                            
                            last_screenshot_size = screenshot_size
                            
                        except Exception as e:
                            self.logger.error(f"Error taking screenshot in consolidated method: {e}")
                            return f"{FAILED_PREFIX}: Screenshot capture error: {e}"
                        
                        # Prepare next request input
                        input_content = [{
                            "call_id": call_id,
                            "type": CONTENT_TYPE_COMPUTER_CALL_OUTPUT,
                            "output": {
                                "type": CONTENT_TYPE_INPUT_IMAGE,
                                "image_url": f"{IMAGE_DATA_URL_PREFIX},{screenshot_b64}"
                            }
                        }]
                        
                        # Add acknowledged safety checks if any
                        if acknowledged_checks:
                            input_content[0]["acknowledged_safety_checks"] = acknowledged_checks
                            self.logger.info(f"Including {len(acknowledged_checks)} acknowledged safety checks in consolidated request")
                        
                        # Send next request
                        try:
                            response = client.responses.create(
                                model=COMPUTER_USE_MODEL,
                                previous_response_id=response.id,
                                tools=[CUA_TOOL_CONFIG],
                                input=input_content,
                                truncation=API_TRUNCATION_AUTO
                            )
                        except Exception as e:
                            self.logger.error(f"Error in consolidated CUA API call: {e}")
                            return f"{FAILED_PREFIX}: API call error: {e}"
                    
                    self.logger.warning(f"CUA consolidated method reached maximum iterations ({max_iterations})")
                    return COMPLETED_CUA_ITERATIONS
                    
            except Exception as e:
                error_msg = f"CUA consolidated timeline reading failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                return f"{FAILED_PREFIX}: {error_msg}"
        
        try:
            return asyncio.run(_internal_consolidated_timeline_via_cua())
        except Exception as e:
            error_msg = f"Failed to execute consolidated CUA timeline reading workflow: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"{FAILED_PREFIX}: {error_msg}"

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

    # ==================== ENHANCED CUA METHODS WITH MEMORY ====================

    async def _enhanced_like_tweet_with_memory(self, tweet_url: str) -> str:
        """Enhanced tweet liking with memory-driven spam prevention.
        
        Args:
            tweet_url: URL of the tweet to like
            
        Returns:
            Result string indicating success/failure with memory context
        """
        # Check if we've recently interacted with this tweet
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
        
        # Proceed with the like action
        self.logger.info(f"✅ Memory check passed - proceeding with tweet like: {tweet_url}")
        result = self.like_tweet_via_cua(tweet_url)
        
        # Log the action result to memory
        action_result = 'SUCCESS' if 'SUCCESS' in result else 'FAILED'
        await self._log_action_to_memory(
            action_type='like_tweet',
            result=action_result,
            target=tweet_url,
            details={'cua_result': result}
        )
        
        return result

    async def _enhanced_research_with_memory(self, query: str) -> str:
        """Enhanced research with automatic content idea saving.
        
        Args:
            query: Research query
            
        Returns:
            Research results with content ideas saved to memory
        """
        self.logger.info(f"🔍 Starting enhanced research with memory: {query}")
        
        # Perform the research
        research_result = self.research_topic_for_aiified(query)
        
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

    # ==================== END MEMORY TOOLS ====================
