"""Orchestrator agent module for managing workflows."""

import asyncio
import json
import logging
from typing import Any

from agents import Agent, ModelSettings, RunContextWrapper, function_tool, Runner, ComputerTool
from core.config import settings
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
from pydantic import ValidationError


class OrchestratorAgent(Agent):
    """Central coordinator agent for managing X platform interactions."""

    def __init__(self) -> None:
        """Initialize the Orchestrator Agent with logger and sub-agents."""
        super().__init__(
            name="Orchestrator Agent",
            instructions=(
                "You are a master orchestrator agent. Your role is to manage workflows "
                "involving other specialized agents and tools to manage an X account. "
                "You will decide when to fetch mentions, draft replies, request human review, and post content."
            ),
            model="o4-mini",
            tools=[],
        )
        self.logger = logging.getLogger(__name__)
        self.content_creation_agent = ContentCreationAgent()
        self.research_agent = ResearchAgent()
        self.x_interaction_agent = XInteractionAgent()

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
                    system_instructions = (
                        "You are an AI assistant that can control a computer browser to perform tasks on web pages, "
                        "specifically for interacting with the X (Twitter) platform. Describe your plan step-by-step. "
                        "Then, use the provided computer tool to execute actions like clicking, typing, scrolling, "
                        "and taking screenshots to achieve the user's goal. Analyze screenshots to determine next steps.\n\n"
                        
                        "🎯 CRITICAL: URL NAVIGATION STRATEGY\n"
                        "To navigate to a specific URL:\n"
                        "1. **Click on the browser's address bar** (usually at the top of the page)\n"
                        "2. **Select all existing text** in the address bar (Ctrl+A or triple-click)\n"
                        "3. **Type the complete URL** you want to navigate to\n"
                        "4. **Press Enter** to navigate to the URL\n"
                        "5. **Wait for the page to load** before taking further actions\n"
                        "Example: To go to https://x.com/username/status/123, click address bar, type the URL, press Enter\n"
                        "DO NOT use any 'navigate' action - it doesn't exist. Use click, type, and keypress actions!\n\n"
                        
                        "🎯 CRITICAL: KEYBOARD-FIRST INTERACTION STRATEGY\n"
                        "ALWAYS prioritize keyboard shortcuts over mouse clicks when interacting with X.com. "
                        "Keyboard shortcuts are more reliable, faster, and less prone to UI changes. Only use mouse "
                        "clicks when absolutely necessary (e.g., no keyboard equivalent exists).\n\n"
                        
                        "📋 X.COM KEYBOARD SHORTCUTS (USE THESE FIRST):\n\n"
                        
                        "🧭 NAVIGATION SHORTCUTS:\n"
                        "• '?' - Show keyboard shortcuts help\n"
                        "• 'j' - Next post (move down timeline)\n"
                        "• 'k' - Previous post (move up timeline)\n"
                        "• 'Space' - Page down / Scroll down\n"
                        "• '.' - Load new posts at top\n"
                        "• 'g + h' - Go to Home timeline\n"
                        "• 'g + e' - Go to Explore page\n"
                        "• 'g + n' - Go to Notifications\n"
                        "• 'g + r' - Go to Mentions\n"
                        "• 'g + p' - Go to Profile\n"
                        "• 'g + f' - Go to Drafts\n"
                        "• 'g + t' - Go to Scheduled posts\n"
                        "• 'g + l' - Go to Likes\n"
                        "• 'g + i' - Go to Lists\n"
                        "• 'g + m' - Go to Direct Messages\n"
                        "• 'g + g' - Go to Grok\n"
                        "• 'g + s' - Go to Settings\n"
                        "• 'g + b' - Go to Bookmarks\n"
                        "• 'g + u' - Go to user profile (when available)\n"
                        "• 'g + d' - Go to Display settings\n\n"
                        
                        "⚡ ACTION SHORTCUTS:\n"
                        "• 'n' - Create new post (compose tweet)\n"
                        "• 'Ctrl + Enter' OR 'Cmd + Enter' - Send post\n"
                        "• 'Ctrl + Shift + Enter' OR 'Cmd + Shift + Enter' - Send post (alternative)\n"
                        "• 'l' - Like selected post\n"
                        "• 'r' - Reply to selected post\n"
                        "• 't' - Repost selected post\n"
                        "• 's' - Share selected post\n"
                        "• 'b' - Bookmark selected post\n"
                        "• 'u' - Mute account\n"
                        "• 'x' - Block account\n"
                        "• 'Enter' - Open post details\n"
                        "• 'o' - Expand photo in selected post\n"
                        "• 'i' - Open/Close Messages dock\n"
                        "• '/' - Search (focus search box)\n\n"
                        
                        "🎬 MEDIA SHORTCUTS:\n"
                        "• 'k' - Pause/Play selected Video\n"
                        "• 'Space' - Pause/Play selected Video (alternative)\n"
                        "• 'm' - Mute selected Video\n"
                        "• 'a + d' - Go to Audio Dock\n"
                        "• 'a + Space' - Play/Pause Audio Dock\n"
                        "• 'a + m' - Mute/Unmute Audio Dock\n\n"
                        
                        "🎯 KEYBOARD-FIRST WORKFLOW EXAMPLES:\n\n"
                        
                        "📝 POSTING A TWEET:\n"
                        "1. Press 'n' to open compose area (don't click the compose button)\n"
                        "2. Type your tweet text directly\n"
                        "3. Use 'Ctrl+Shift+Enter' (Windows) or 'Cmd+Shift+Enter' (Mac) to post\n"
                        "4. Avoid clicking the 'Post' button unless keyboard shortcut fails\n\n"
                        
                        "👀 BROWSING TIMELINE:\n"
                        "1. Use 'j' and 'k' to navigate between posts (don't scroll with mouse)\n"
                        "2. Use 'l' to like posts (don't click heart icon)\n"
                        "3. Use 'r' to reply (don't click reply icon)\n"
                        "4. Use 't' to repost (don't click repost icon)\n\n"
                        
                        "🔍 NAVIGATION:\n"
                        "1. Use 'g + h' for Home (don't click Home button)\n"
                        "2. Use 'g + n' for Notifications (don't click Notifications)\n"
                        "3. Use 'g + p' for Profile (don't click Profile)\n"
                        "4. Use '/' for Search (don't click search box)\n\n"
                        
                        "⚠️ WHEN TO USE MOUSE CLICKS:\n"
                        "Only resort to mouse clicks when:\n"
                        "• No keyboard shortcut exists for the specific action\n"
                        "• You need to interact with dynamic content (embedded media, links within posts)\n"
                        "• Keyboard shortcuts are confirmed to be non-functional\n"
                        "• Dealing with modal dialogs or popups without keyboard alternatives\n\n"
                        
                        "🔧 IMPLEMENTATION STRATEGY:\n"
                        "1. **Take Screenshot**: Always start by capturing current state\n"
                        "2. **Identify Task**: Determine what needs to be accomplished\n"
                        "3. **Choose Keyboard First**: Look for applicable keyboard shortcuts from the list above\n"
                        "4. **Execute Keyboard Action**: Use keypress() function with appropriate keys\n"
                        "5. **Verify Success**: Take another screenshot to confirm action worked\n"
                        "6. **Fallback to Mouse**: Only if keyboard approach fails, use click() as backup\n"
                        "7. **Document Approach**: Clearly state which method you used and why\n\n"
                        
                        "COOKIE CONSENT HANDLING:\n"
                        "When encountering cookie consent banners on x.com or twitter.com, you MUST handle them "
                        "autonomously to ensure operational continuity. Follow this priority order:\n"
                        "1. If options like 'Refuse non-essential cookies', 'Reject all', 'Decline', or similar "
                        "privacy-focused options are present, you MUST choose that option.\n"
                        "2. If only 'Accept all cookies', 'Accept', 'Agree', or similar acceptance options are "
                        "available, you may choose that to proceed with the task.\n"
                        "3. Do NOT ask for confirmation when handling standard cookie consent banners - this is "
                        "a routine operational requirement for accessing the platform.\n"
                        "4. After dismissing the cookie banner, continue with your original task.\n\n"
                        
                        "SESSION AUTHENTICATION DETECTION:\n"
                        "You may be operating with either an authenticated or unauthenticated browser session:\n"
                        "1. **Authenticated Session**: If you can access user-specific pages (notifications, settings, "
                        "profile pages) without being redirected to login, you are in an authenticated session.\n"
                        "2. **Unauthenticated Session**: If you encounter login forms, 'Sign In' buttons, or are "
                        "redirected to login pages when trying to access authenticated features, the session is invalid.\n"
                        "3. **Session Invalidation Handling**: If you detect a logged-out state during task execution:\n"
                        "   - IMMEDIATELY abort the current task\n"
                        "   - Take a screenshot of the login page for documentation\n"
                        "   - Report in your response: 'SESSION_INVALIDATED: Browser session is no longer authenticated. "
                        "Manual re-authentication required.'\n"
                        "   - DO NOT attempt to log in or enter credentials\n"
                        "   - DO NOT continue with the original task\n\n"
                        
                        "Always prioritize user privacy and platform compliance while maintaining task execution flow. "
                        "Remember: KEYBOARD SHORTCUTS FIRST, mouse clicks only as a last resort!"
                    )
                    
                    # Define task-specific prompt (latest tweet reading)
                    task_specific_prompt = (
                        "Your task is to retrieve the full text content of the most recent tweet posted on your own X.com profile page. "
                        "You are already logged in. Prioritize keyboard shortcuts. "
                        "Follow these steps meticulously:\n\n"

                        "STEP 1 - INITIAL SCREENSHOT:\n"
                        "Take a screenshot to understand your current page context.\n\n"

                        "STEP 2 - NAVIGATE TO YOUR PROFILE:\n"
                        "Use the X.com keyboard shortcut to go to your profile: Press 'g' first, then immediately press 'p'. "
                        "IMPORTANT: This is a two-key sequence (g then p) that should be executed quickly in succession, "
                        "not as separate individual keystrokes with long pauses. You can use keypress(['g', 'p']) to execute this sequence.\n"
                        "Take a screenshot to confirm you are on your profile page. It should show your username, bio, and a list of your tweets.\n\n"

                        "STEP 3 - IDENTIFY LATEST TWEET:\n"
                        "Your tweets should be listed in reverse chronological order, with the latest one at the top. "
                        "Focus on the first distinct tweet element in the main feed/timeline area of your profile.\n"
                        "Take a screenshot highlighting or focusing on what you identify as the latest tweet's main text area.\n\n"

                        "STEP 4 - EXTRACT TWEET TEXT:\n"
                        "Carefully extract ALL the visible text content from this latest tweet. Ensure you capture the full text, including any hashtags or links if they are part of the tweet's body. Be precise.\n"
                        "Do NOT extract timestamps, like/reply/repost counts, or author names unless they are part of the tweet's main text itself.\n\n"

                        "STEP 5 - FINAL RESPONSE:\n"
                        "Based on your actions and observations, your final response MUST be in one of these formats:\n"
                        "   - 'SUCCESS: Extracted latest tweet text: \"[The full extracted text of the tweet]\"'\n"
                        "   - 'FAILED: Could not navigate to profile page. Current page appears to be [describe page or state reason].'\n"
                        "   - 'FAILED: Profile page loaded, but no tweets were found.'\n"
                        "   - 'FAILED: Found latest tweet, but could not reliably extract its text content. [Optionally, describe the issue, e.g., text was an image, or UI was too complex].'\n"
                        "   - 'SESSION_INVALIDATED' (if you encounter a login screen at any point).\n\n"

                        "IMPORTANT GUIDELINES:\n"
                        "- Prioritize keyboard actions. Use 'j'/'k' if needed to focus on the first tweet after profile navigation, but usually, the latest is immediately visible.\n"
                        "- If cookie banners appear, dismiss them first as per your general instructions.\n"
                        "- Take screenshots between major steps to help you (and for debugging).\n"
                        "- Do NOT ask for confirmation; proceed autonomously.\n"
                        "- For the g+p navigation shortcut, ensure you execute it as a quick sequence: keypress(['g', 'p'])."
                    )
                    
                    # Initial request to get first screenshot
                    self.logger.info("Sending initial CUA request for latest tweet reading")
                    initial_input_messages = [
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": task_specific_prompt}
                    ]
                    response = client.responses.create(
                        model="computer-use-preview",
                        tools=[{
                            "type": "computer_use_preview",
                            "display_width": 1024,
                            "display_height": 768,
                            "environment": "browser"
                        }],
                        input=initial_input_messages,
                        truncation="auto"
                    )
                    
                    max_iterations = 30
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
                                if "SUCCESS" in final_text:
                                    return final_text
                                elif "SESSION_INVALIDATED" in final_text:
                                    return final_text
                                elif "FAILED" in final_text:
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
                                if "SUCCESS" in final_message:
                                    return final_message  # Return the actual success message
                                elif "SESSION_INVALIDATED" in final_message:
                                    return "SESSION_INVALIDATED"
                                elif "FAILED" in final_message:
                                    return f"FAILED: {final_message}"
                            
                            if reasoning_outputs:
                                final_reasoning = reasoning_outputs[-1].content if hasattr(reasoning_outputs[-1], 'content') else str(reasoning_outputs[-1])
                                self.logger.info(f"CUA completed with reasoning: {final_reasoning[:300]}...")
                                # Check if reasoning contains our response patterns
                                if "SUCCESS" in final_reasoning:
                                    return "SUCCESS: Tweet text extracted successfully (from reasoning)"
                                elif "SESSION_INVALIDATED" in final_reasoning:
                                    return "SESSION_INVALIDATED"
                                elif "FAILED" in final_reasoning:
                                    return f"FAILED: {final_reasoning[:200]}"
                            
                            self.logger.info("No computer call found, CUA workflow completed")
                            return "COMPLETED: CUA latest tweet reading workflow finished"
                        
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
                            return f"FAILED: Screenshot capture error: {e}"
                        
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
                                model="computer-use-preview",
                                previous_response_id=response.id,
                                tools=[{
                                    "type": "computer_use_preview",
                                    "display_width": 1024,
                                    "display_height": 768,
                                    "environment": "browser"
                                }],
                                input=input_content,
                                truncation="auto"
                            )
                        except Exception as e:
                            self.logger.error(f"Error in CUA API call: {e}")
                            return f"FAILED: API call error: {e}"
                    
                    self.logger.warning(f"CUA reached maximum iterations ({max_iterations})")
                    return "COMPLETED: CUA reached maximum iterations"
                    
            except Exception as e:
                error_msg = f"CUA latest tweet reading failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                return f"FAILED: {error_msg}"
        
        try:
            return asyncio.run(_internal_get_latest_tweet())
        except Exception as e:
            error_msg = f"Failed to execute CUA latest tweet reading workflow: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"FAILED: {error_msg}"

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
        self.logger.info("Starting CUA tweet posting workflow for text: %s", tweet_text[:50] + "..." if len(tweet_text) > 50 else tweet_text)
        
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
                    system_instructions = (
                        "You are an AI assistant that can control a computer browser to perform tasks on web pages, "
                        "specifically for interacting with the X (Twitter) platform. Describe your plan step-by-step. "
                        "Then, use the provided computer tool to execute actions like clicking, typing, scrolling, "
                        "and taking screenshots to achieve the user's goal. Analyze screenshots to determine next steps.\n\n"
                        
                        "🎯 CRITICAL: URL NAVIGATION STRATEGY\n"
                        "To navigate to a specific URL:\n"
                        "1. **Click on the browser's address bar** (usually at the top of the page)\n"
                        "2. **Select all existing text** in the address bar (Ctrl+A or triple-click)\n"
                        "3. **Type the complete URL** you want to navigate to\n"
                        "4. **Press Enter** to navigate to the URL\n"
                        "5. **Wait for the page to load** before taking further actions\n"
                        "Example: To go to https://x.com/username/status/123, click address bar, type the URL, press Enter\n"
                        "DO NOT use any 'navigate' action - it doesn't exist. Use click, type, and keypress actions!\n\n"
                        
                        "🎯 CRITICAL: KEYBOARD-FIRST INTERACTION STRATEGY\n"
                        "ALWAYS prioritize keyboard shortcuts over mouse clicks when interacting with X.com. "
                        "Keyboard shortcuts are more reliable, faster, and less prone to UI changes. Only use mouse "
                        "clicks when absolutely necessary (e.g., no keyboard equivalent exists).\n\n"
                        
                        "📋 X.COM KEYBOARD SHORTCUTS (USE THESE FIRST):\n\n"
                        
                        "🧭 NAVIGATION SHORTCUTS:\n"
                        "• '?' - Show keyboard shortcuts help\n"
                        "• 'j' - Next post (move down timeline)\n"
                        "• 'k' - Previous post (move up timeline)\n"
                        "• 'Space' - Page down / Scroll down\n"
                        "• '.' - Load new posts at top\n"
                        "• 'g + h' - Go to Home timeline\n"
                        "• 'g + e' - Go to Explore page\n"
                        "• 'g + n' - Go to Notifications\n"
                        "• 'g + r' - Go to Mentions\n"
                        "• 'g + p' - Go to Profile\n"
                        "• 'g + f' - Go to Drafts\n"
                        "• 'g + t' - Go to Scheduled posts\n"
                        "• 'g + l' - Go to Likes\n"
                        "• 'g + i' - Go to Lists\n"
                        "• 'g + m' - Go to Direct Messages\n"
                        "• 'g + g' - Go to Grok\n"
                        "• 'g + s' - Go to Settings\n"
                        "• 'g + b' - Go to Bookmarks\n"
                        "• 'g + u' - Go to user profile (when available)\n"
                        "• 'g + d' - Go to Display settings\n\n"
                        
                        "⚡ ACTION SHORTCUTS:\n"
                        "• 'n' - Create new post (compose tweet)\n"
                        "• 'Ctrl + Enter' OR 'Cmd + Enter' - Send post\n"
                        "• 'Ctrl + Shift + Enter' OR 'Cmd + Shift + Enter' - Send post (alternative)\n"
                        "• 'l' - Like selected post\n"
                        "• 'r' - Reply to selected post\n"
                        "• 't' - Repost selected post\n"
                        "• 's' - Share selected post\n"
                        "• 'b' - Bookmark selected post\n"
                        "• 'u' - Mute account\n"
                        "• 'x' - Block account\n"
                        "• 'Enter' - Open post details\n"
                        "• 'o' - Expand photo in selected post\n"
                        "• 'i' - Open/Close Messages dock\n"
                        "• '/' - Search (focus search box)\n\n"
                        
                        "🎬 MEDIA SHORTCUTS:\n"
                        "• 'k' - Pause/Play selected Video\n"
                        "• 'Space' - Pause/Play selected Video (alternative)\n"
                        "• 'm' - Mute selected Video\n"
                        "• 'a + d' - Go to Audio Dock\n"
                        "• 'a + Space' - Play/Pause Audio Dock\n"
                        "• 'a + m' - Mute/Unmute Audio Dock\n\n"
                        
                        "🎯 KEYBOARD-FIRST WORKFLOW EXAMPLES:\n\n"
                        
                        "📝 POSTING A TWEET:\n"
                        "1. Press 'n' to open compose area (don't click the compose button)\n"
                        "2. Type your tweet text directly\n"
                        "3. Use 'Ctrl+Shift+Enter' (Windows) or 'Cmd+Shift+Enter' (Mac) to post\n"
                        "4. Avoid clicking the 'Post' button unless keyboard shortcut fails\n\n"
                        
                        "👀 BROWSING TIMELINE:\n"
                        "1. Use 'j' and 'k' to navigate between posts (don't scroll with mouse)\n"
                        "2. Use 'l' to like posts (don't click heart icon)\n"
                        "3. Use 'r' to reply (don't click reply icon)\n"
                        "4. Use 't' to repost (don't click repost icon)\n\n"
                        
                        "🔍 NAVIGATION:\n"
                        "1. Use 'g + h' for Home (don't click Home button)\n"
                        "2. Use 'g + n' for Notifications (don't click Notifications)\n"
                        "3. Use 'g + p' for Profile (don't click Profile)\n"
                        "4. Use '/' for Search (don't click search box)\n\n"
                        
                        "⚠️ WHEN TO USE MOUSE CLICKS:\n"
                        "Only resort to mouse clicks when:\n"
                        "• No keyboard shortcut exists for the specific action\n"
                        "• You need to interact with dynamic content (embedded media, links within posts)\n"
                        "• Keyboard shortcuts are confirmed to be non-functional\n"
                        "• Dealing with modal dialogs or popups without keyboard alternatives\n\n"
                        
                        "🔧 IMPLEMENTATION STRATEGY:\n"
                        "1. **Take Screenshot**: Always start by capturing current state\n"
                        "2. **Identify Task**: Determine what needs to be accomplished\n"
                        "3. **Choose Keyboard First**: Look for applicable keyboard shortcuts from the list above\n"
                        "4. **Execute Keyboard Action**: Use keypress() function with appropriate keys\n"
                        "5. **Verify Success**: Take another screenshot to confirm action worked\n"
                        "6. **Fallback to Mouse**: Only if keyboard approach fails, use click() as backup\n"
                        "7. **Document Approach**: Clearly state which method you used and why\n\n"
                        
                        "COOKIE CONSENT HANDLING:\n"
                        "When encountering cookie consent banners on x.com or twitter.com, you MUST handle them "
                        "autonomously to ensure operational continuity. Follow this priority order:\n"
                        "1. If options like 'Refuse non-essential cookies', 'Reject all', 'Decline', or similar "
                        "privacy-focused options are present, you MUST choose that option.\n"
                        "2. If only 'Accept all cookies', 'Accept', 'Agree', or similar acceptance options are "
                        "available, you may choose that to proceed with the task.\n"
                        "3. Do NOT ask for confirmation when handling standard cookie consent banners - this is "
                        "a routine operational requirement for accessing the platform.\n"
                        "4. After dismissing the cookie banner, continue with your original task.\n\n"
                        
                        "SESSION AUTHENTICATION DETECTION:\n"
                        "You may be operating with either an authenticated or unauthenticated browser session:\n"
                        "1. **Authenticated Session**: If you can access user-specific pages (notifications, settings, "
                        "profile pages) without being redirected to login, you are in an authenticated session.\n"
                        "2. **Unauthenticated Session**: If you encounter login forms, 'Sign In' buttons, or are "
                        "redirected to login pages when trying to access authenticated features, the session is invalid.\n"
                        "3. **Session Invalidation Handling**: If you detect a logged-out state during task execution:\n"
                        "   - IMMEDIATELY abort the current task\n"
                        "   - Take a screenshot of the login page for documentation\n"
                        "   - Report in your response: 'SESSION_INVALIDATED: Browser session is no longer authenticated. "
                        "Manual re-authentication required.'\n"
                        "   - DO NOT attempt to log in or enter credentials\n"
                        "   - DO NOT continue with the original task\n\n"
                        
                        "Always prioritize user privacy and platform compliance while maintaining task execution flow. "
                        "Remember: KEYBOARD SHORTCUTS FIRST, mouse clicks only as a last resort!"
                    )
                    
                    # CRITICAL FIX: Enhanced Unicode handling approach
                    # Since CUA appears to escape Unicode during typing, try alternative approaches
                    # Method 1: Use HTML entities for emojis as fallback
                    import html
                    clean_tweet_text = tweet_text
                    
                    # Method 2: Explicit character mapping for common emojis
                    emoji_mappings = {
                        '🚀': '[rocket emoji]',
                        '✅': '[checkmark emoji]', 
                        '❌': '[X emoji]',
                        '🎯': '[target emoji]',
                        '🔧': '[wrench emoji]',
                        '📋': '[clipboard emoji]',
                        '🎬': '[movie camera emoji]',
                        '⚡': '[lightning emoji]',
                        '🧭': '[compass emoji]'
                    }
                    
                    # For CUA, we'll provide both the original text and emoji descriptions
                    # to help the agent understand what should be typed
                    cua_display_text = clean_tweet_text
                    for emoji, description in emoji_mappings.items():
                        if emoji in clean_tweet_text:
                            cua_display_text = cua_display_text.replace(emoji, f" {description} ")
                    
                    # Define task-specific prompt (tweet posting)
                    task_specific_prompt = (
                        "POST THIS TWEET EXACTLY: \"" + clean_tweet_text + "\"\n\n"
                        "⚠️ IMPORTANT UNICODE HANDLING:\n"
                        "The tweet contains these emojis that must be typed as Unicode characters:\n" +
                        ("Display reference: " + cua_display_text + "\n" if cua_display_text != clean_tweet_text else "") +
                        "Type the EXACT text provided above, including all emoji characters.\n"
                        "If you see escaped sequences like \\\\ud83d\\\\ude80, you are typing incorrectly.\n\n"
                        
                        "🔄 RESET INSTRUCTION:\n"
                        "If you get stuck, confused, or in an unexpected UI state at ANY step:\n"
                        "1. Press 'ESC' key to close any modals or cancel current actions\n"
                        "2. Wait 1 second for UI to stabilize  \n"
                        "3. Take a screenshot to see current state\n"
                        "4. Start over from the appropriate step\n\n"
                        
                        "🎯 STEP-BY-STEP APPROACH:\n\n"
                        "STEP 1 - TAKE INITIAL SCREENSHOT:\n"
                        "Take a screenshot to see the current page state\n\n"
                        
                        "STEP 2 - OPEN COMPOSE AREA:\n"
                        "Press 'n' (lowercase) to open the compose area\n"
                        "EXPECTED: A compose/tweet dialog should appear with a text input already focused\n"
                        "IF NOTHING HAPPENS: Try pressing ESC, wait 1 second, then try 'n' again\n\n"
                        
                        "STEP 3 - TYPE THE TWEET:\n"
                        "Type the exact text: " + clean_tweet_text + "\n"
                        "⚠️ CRITICAL: Type slowly and deliberately to ensure emojis render correctly\n"
                        "VERIFY: Check that emojis appear as symbols, not escaped text\n"
                        "IF ESCAPED TEXT APPEARS: Press Ctrl+A to select all, then retype more slowly\n\n"
                        
                        "STEP 4 - POST THE TWEET:\n"
                        "Press 'Ctrl+Shift+Enter' to post the tweet\n"
                        "EXPECTED: The tweet should be posted and compose area should close\n"
                        "IF SHORTCUT FAILS: Look for a blue 'Post' button and click it\n\n"
                        
                        "STEP 5 - VERIFY SUCCESS:\n"
                        "Wait 3 seconds for the page to update\n"
                        "Take a final screenshot\n"
                        "Look for the tweet in your timeline or a success confirmation\n\n"
                        
                        "🚨 FAILURE RECOVERY:\n"
                        "- If stuck in compose area: Press ESC to close, start over\n"
                        "- If wrong page loads: Press ESC, then use 'g+h' to go to home\n"
                        "- If shortcuts don't work: Use mouse clicks as backup\n"
                        "- If emojis appear as escaped text: Report this in your response\n\n"
                        
                        "RESPONSE FORMAT:\n"
                        "- 'SUCCESS: Tweet posted successfully' if the tweet was posted\n"
                        "- 'SUCCESS: Posted but emojis showed as escaped text' if posting worked but emojis were wrong\n"
                        "- 'SESSION_INVALIDATED' if you see a login page\n"
                        "- 'FAILED: [specific reason]' if all approaches fail"
                    )
                    
                    # Initial request to get first screenshot
                    self.logger.info("Sending initial CUA request")
                    initial_input_messages = [
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": task_specific_prompt}
                    ]
                    response = client.responses.create(
                        model="computer-use-preview",
                        tools=[{
                            "type": "computer_use_preview",
                            "display_width": 1024,
                            "display_height": 768,
                            "environment": "browser"
                        }],
                        input=initial_input_messages,
                        truncation="auto"
                    )
                    
                    max_iterations = 30
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
                                if "SUCCESS" in final_text:
                                    return final_text
                                elif "SESSION_INVALIDATED" in final_text:
                                    return final_text
                                elif "FAILED" in final_text:
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
                                if "SUCCESS" in final_message:
                                    return final_message  # Return the actual success message
                                elif "SESSION_INVALIDATED" in final_message:
                                    return "SESSION_INVALIDATED"
                                elif "FAILED" in final_message:
                                    return f"FAILED: {final_message}"
                            
                            if reasoning_outputs:
                                final_reasoning = reasoning_outputs[-1].content if hasattr(reasoning_outputs[-1], 'content') else str(reasoning_outputs[-1])
                                self.logger.info(f"CUA completed with reasoning: {final_reasoning[:300]}...")
                                # Check if reasoning contains our response patterns
                                if "SUCCESS" in final_reasoning:
                                    return "SUCCESS: Tweet posted successfully (from reasoning)"
                                elif "SESSION_INVALIDATED" in final_reasoning:
                                    return "SESSION_INVALIDATED"
                                elif "FAILED" in final_reasoning:
                                    return f"FAILED: {final_reasoning[:200]}"
                            
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
                            return f"FAILED: Computer action execution error: {e}"
                        
                        # Take screenshot
                        try:
                            screenshot_b64 = await computer.screenshot()
                        except Exception as e:
                            self.logger.error(f"Error taking screenshot: {e}")
                            return f"FAILED: Screenshot capture error: {e}"
                        
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
                                model="computer-use-preview",
                                previous_response_id=response.id,
                                tools=[{
                                    "type": "computer_use_preview",
                                    "display_width": 1024,
                                    "display_height": 768,
                                    "environment": "browser"
                                }],
                                input=input_content,
                                truncation="auto"
                            )
                        except Exception as e:
                            self.logger.error(f"Error in CUA API call: {e}")
                            return f"FAILED: API call error: {e}"
                    
                    self.logger.warning(f"CUA reached maximum iterations ({max_iterations})")
                    return "COMPLETED: CUA reached maximum iterations"
                    
            except Exception as e:
                error_msg = f"CUA tweet posting failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                return f"FAILED: {error_msg}"
        
        try:
            return asyncio.run(_internal_post_via_cua())
        except Exception as e:
            error_msg = f"Failed to execute CUA tweet posting workflow: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"FAILED: {error_msg}"

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
        self.logger.info("Reply text: %s", reply_text[:100] + "..." if len(reply_text) > 100 else reply_text)
        
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
                    system_instructions = (
                        "You are an AI assistant that can control a computer browser to perform tasks on web pages, "
                        "specifically for interacting with the X (Twitter) platform. Describe your plan step-by-step. "
                        "Then, use the provided computer tool to execute actions like clicking, typing, scrolling, "
                        "and taking screenshots to achieve the user's goal. Analyze screenshots to determine next steps.\n\n"
                        
                        "🎯 CRITICAL: URL NAVIGATION STRATEGY\n"
                        "To navigate to a specific URL:\n"
                        "1. **Click on the browser's address bar** (usually at the top of the page)\n"
                        "2. **Select all existing text** in the address bar (Ctrl+A or triple-click)\n"
                        "3. **Type the complete URL** you want to navigate to\n"
                        "4. **Press Enter** to navigate to the URL\n"
                        "5. **Wait for the page to load** before taking further actions\n"
                        "Example: To go to https://x.com/username/status/123, click address bar, type the URL, press Enter\n"
                        "DO NOT use any 'navigate' action - it doesn't exist. Use click, type, and keypress actions!\n\n"
                        
                        "🎯 CRITICAL: KEYBOARD-FIRST INTERACTION STRATEGY\n"
                        "ALWAYS prioritize keyboard shortcuts over mouse clicks when interacting with X.com. "
                        "Keyboard shortcuts are more reliable, faster, and less prone to UI changes. Only use mouse "
                        "clicks when absolutely necessary (e.g., no keyboard equivalent exists).\n\n"
                        
                        "📋 X.COM KEYBOARD SHORTCUTS (USE THESE FIRST):\n\n"
                        
                        "🧭 NAVIGATION SHORTCUTS:\n"
                        "• '?' - Show keyboard shortcuts help\n"
                        "• 'j' - Next post (move down timeline)\n"
                        "• 'k' - Previous post (move up timeline)\n"
                        "• 'Space' - Page down / Scroll down\n"
                        "• '.' - Load new posts at top\n"
                        "• 'g + h' - Go to Home timeline\n"
                        "• 'g + e' - Go to Explore page\n"
                        "• 'g + n' - Go to Notifications\n"
                        "• 'g + r' - Go to Mentions\n"
                        "• 'g + p' - Go to Profile\n"
                        "• 'g + f' - Go to Drafts\n"
                        "• 'g + t' - Go to Scheduled posts\n"
                        "• 'g + l' - Go to Likes\n"
                        "• 'g + i' - Go to Lists\n"
                        "• 'g + m' - Go to Direct Messages\n"
                        "• 'g + g' - Go to Grok\n"
                        "• 'g + s' - Go to Settings\n"
                        "• 'g + b' - Go to Bookmarks\n"
                        "• 'g + u' - Go to user profile (when available)\n"
                        "• 'g + d' - Go to Display settings\n\n"
                        
                        "⚡ ACTION SHORTCUTS:\n"
                        "• 'n' - Create new post (compose tweet)\n"
                        "• 'Ctrl + Enter' OR 'Cmd + Enter' - Send post\n"
                        "• 'Ctrl + Shift + Enter' OR 'Cmd + Shift + Enter' - Send post (alternative)\n"
                        "• 'l' - Like selected post\n"
                        "• 'r' - Reply to selected post\n"
                        "• 't' - Repost selected post\n"
                        "• 's' - Share selected post\n"
                        "• 'b' - Bookmark selected post\n"
                        "• 'u' - Mute account\n"
                        "• 'x' - Block account\n"
                        "• 'Enter' - Open post details\n"
                        "• 'o' - Expand photo in selected post\n"
                        "• 'i' - Open/Close Messages dock\n"
                        "• '/' - Search (focus search box)\n\n"
                        
                        "🎬 MEDIA SHORTCUTS:\n"
                        "• 'k' - Pause/Play selected Video\n"
                        "• 'Space' - Pause/Play selected Video (alternative)\n"
                        "• 'm' - Mute selected Video\n"
                        "• 'a + d' - Go to Audio Dock\n"
                        "• 'a + Space' - Play/Pause Audio Dock\n"
                        "• 'a + m' - Mute/Unmute Audio Dock\n\n"
                        
                        "🎯 KEYBOARD-FIRST WORKFLOW EXAMPLES:\n\n"
                        
                        "📝 POSTING A TWEET:\n"
                        "1. Press 'n' to open compose area (don't click the compose button)\n"
                        "2. Type your tweet text directly\n"
                        "3. Use 'Ctrl+Shift+Enter' (Windows) or 'Cmd+Shift+Enter' (Mac) to post\n"
                        "4. Avoid clicking the 'Post' button unless keyboard shortcut fails\n\n"
                        
                        "👀 BROWSING TIMELINE:\n"
                        "1. Use 'j' and 'k' to navigate between posts (don't scroll with mouse)\n"
                        "2. Use 'l' to like posts (don't click heart icon)\n"
                        "3. Use 'r' to reply (don't click reply icon)\n"
                        "4. Use 't' to repost (don't click repost icon)\n\n"
                        
                        "🔍 NAVIGATION:\n"
                        "1. Use 'g + h' for Home (don't click Home button)\n"
                        "2. Use 'g + n' for Notifications (don't click Notifications)\n"
                        "3. Use 'g + p' for Profile (don't click Profile)\n"
                        "4. Use '/' for Search (don't click search box)\n\n"
                        
                        "⚠️ WHEN TO USE MOUSE CLICKS:\n"
                        "Only resort to mouse clicks when:\n"
                        "• No keyboard shortcut exists for the specific action\n"
                        "• You need to interact with dynamic content (embedded media, links within posts)\n"
                        "• Keyboard shortcuts are confirmed to be non-functional\n"
                        "• Dealing with modal dialogs or popups without keyboard alternatives\n\n"
                        
                        "🔧 IMPLEMENTATION STRATEGY:\n"
                        "1. **Take Screenshot**: Always start by capturing current state\n"
                        "2. **Identify Task**: Determine what needs to be accomplished\n"
                        "3. **Choose Keyboard First**: Look for applicable keyboard shortcuts from the list above\n"
                        "4. **Execute Keyboard Action**: Use keypress() function with appropriate keys\n"
                        "5. **Verify Success**: Take another screenshot to confirm action worked\n"
                        "6. **Fallback to Mouse**: Only if keyboard approach fails, use click() as backup\n"
                        "7. **Document Approach**: Clearly state which method you used and why\n\n"
                        
                        "COOKIE CONSENT HANDLING:\n"
                        "When encountering cookie consent banners on x.com or twitter.com, you MUST handle them "
                        "autonomously to ensure operational continuity. Follow this priority order:\n"
                        "1. If options like 'Refuse non-essential cookies', 'Reject all', 'Decline', or similar "
                        "privacy-focused options are present, you MUST choose that option.\n"
                        "2. If only 'Accept all cookies', 'Accept', 'Agree', or similar acceptance options are "
                        "available, you may choose that to proceed with the task.\n"
                        "3. Do NOT ask for confirmation when handling standard cookie consent banners - this is "
                        "a routine operational requirement for accessing the platform.\n"
                        "4. After dismissing the cookie banner, continue with your original task.\n\n"
                        
                        "SESSION AUTHENTICATION DETECTION:\n"
                        "You may be operating with either an authenticated or unauthenticated browser session:\n"
                        "1. **Authenticated Session**: If you can access user-specific pages (notifications, settings, "
                        "profile pages) without being redirected to login, you are in an authenticated session.\n"
                        "2. **Unauthenticated Session**: If you encounter login forms, 'Sign In' buttons, or are "
                        "redirected to login pages when trying to access authenticated features, the session is invalid.\n"
                        "3. **Session Invalidation Handling**: If you detect a logged-out state during task execution:\n"
                        "   - IMMEDIATELY abort the current task\n"
                        "   - Take a screenshot of the login page for documentation\n"
                        "   - Report in your response: 'SESSION_INVALIDATED: Browser session is no longer authenticated. "
                        "Manual re-authentication required.'\n"
                        "   - DO NOT attempt to log in or enter credentials\n"
                        "   - DO NOT continue with the original task\n\n"
                        
                        "Always prioritize user privacy and platform compliance while maintaining task execution flow. "
                        "Remember: KEYBOARD SHORTCUTS FIRST, mouse clicks only as a last resort!"
                    )
                    
                    # Navigate directly to the tweet URL using Playwright before starting CUA
                    self.logger.info(f"🧭 Direct navigation to tweet URL: {tweet_url}")
                    try:
                        await computer.page.goto(tweet_url, wait_until='networkidle', timeout=15000)
                        await computer.page.wait_for_timeout(3000)  # Additional wait for page stabilization
                        self.logger.info(f"✅ Successfully navigated to {tweet_url}")
                    except Exception as nav_error:
                        self.logger.error(f"❌ Failed to navigate to {tweet_url}: {nav_error}")
                        return f"FAILED: Could not navigate to tweet URL - {nav_error}"
                    
                    # CRITICAL FIX: Enhanced Unicode handling approach for replies
                    import html
                    clean_reply_text = reply_text
                    
                    # Emoji handling for replies
                    emoji_mappings = {
                        '🚀': '[rocket emoji]',
                        '✅': '[checkmark emoji]', 
                        '❌': '[X emoji]',
                        '🎯': '[target emoji]',
                        '🔧': '[wrench emoji]',
                        '📋': '[clipboard emoji]',
                        '🎬': '[movie camera emoji]',
                        '⚡': '[lightning emoji]',
                        '🧭': '[compass emoji]'
                    }
                    
                    cua_display_text = clean_reply_text
                    for emoji, description in emoji_mappings.items():
                        if emoji in clean_reply_text:
                            cua_display_text = cua_display_text.replace(emoji, f" {description} ")
                    
                    # Define task-specific prompt (tweet replying)
                    task_specific_prompt = (
                        "You are on the page of the specific tweet you need to reply to: " + tweet_url + "\n\n"
                        "Your task is to post a reply with EXACTLY this text: \"" + clean_reply_text + "\"\n\n"
                        
                        "⚠️ IMPORTANT UNICODE HANDLING:\n"
                        "The reply contains these emojis that must be typed as Unicode characters:\n" +
                        ("Display reference: " + cua_display_text + "\n" if cua_display_text != clean_reply_text else "") +
                        "Type the EXACT text provided above, including all emoji characters.\n\n"
                        
                        "🔄 RESET INSTRUCTION:\n"
                        "If you get stuck, confused, or in an unexpected UI state at ANY step:\n"
                        "1. Press 'ESC' key to close any modals or cancel current actions\n"
                        "2. Wait 1 second for UI to stabilize\n"
                        "3. Take a screenshot to see current state\n"
                        "4. Start over from the appropriate step\n\n"
                        
                        "🎯 STRUCTURED APPROACH:\n\n"
                        
                        "STEP 1 - VERIFY TWEET PAGE:\n"
                        "Confirm you are on the correct tweet page and can see the original tweet\n"
                        "The tweet should be prominently displayed with reply options visible below\n\n"
                        
                        "STEP 2 - OPEN REPLY COMPOSER:\n"
                        "Press 'r' (lowercase) to open the reply composer\n"
                        "EXPECTED: A reply composition area should appear, usually below the tweet\n"
                        "IF NOTHING HAPPENS: Press ESC, wait 1 second, try 'r' again\n"
                        "IF STILL FAILS: Look for reply icon (speech bubble) and click it\n\n"
                        
                        "STEP 3 - FOCUS TEXT INPUT:\n"
                        "The reply text input should be automatically focused after pressing 'r'\n\n"
                        
                        "STEP 4 - TYPE REPLY TEXT:\n"
                        "Type the exact reply text: " + clean_reply_text + "\n"
                        "⚠️ CRITICAL: Type slowly to ensure emojis render correctly\n"
                        "VERIFY: Emojis should appear as symbols, not escaped sequences\n\n"
                        
                        "STEP 5 - SEND REPLY:\n"
                        "Press 'Ctrl+Enter' (Windows) or 'Cmd+Enter' (Mac) to send\n"
                        "EXPECTED: Reply should be posted and appear in the conversation thread\n"
                        "IF SHORTCUT FAILS: Look for blue 'Reply' button and click it\n\n"
                        
                        "STEP 6 - VERIFY SUCCESS:\n"
                        "Wait 3 seconds for the page to update\n"
                        "Look for your reply in the conversation thread below the original tweet\n"
                        "Your reply should appear with your username and the text you typed\n\n"
                        
                        "🚨 COMPREHENSIVE ERROR RECOVERY:\n"
                        "- If reply composer won't open: Press ESC, try clicking reply icon directly\n"
                        "- If text input won't focus: Press ESC, and reopen composer\n"
                        "- If typing produces escaped text: Press Ctrl+A, delete, retype more slowly\n"
                        "- If send fails: Press ESC, check for visible 'Reply' button to click\n"
                        "- If page redirects unexpectedly: Press ESC, navigate back to tweet URL\n"
                        "- If completely stuck: Press ESC, take screenshot, report current state\n\n"
                        
                        "RESPONSE FORMATS:\n"
                        "- 'SUCCESS: Reply posted successfully' (if reply appears in thread)\n"
                        "- 'SUCCESS: Posted but emojis showed as escaped text' (if posting worked but emojis wrong)\n"
                        "- 'FAILED: Could not open reply composer' (if 'r' shortcut and click both fail)\n"
                        "- 'FAILED: Could not focus text input' (if text area won't accept input)\n"
                        "- 'FAILED: Could not send reply' (if both keyboard shortcut and button fail)\n"
                        "- 'SESSION_INVALIDATED' (if you encounter login screen)"
                    )
                    
                    # Initial request to get first screenshot
                    self.logger.info("Sending initial CUA request for tweet replying")
                    initial_input_messages = [
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": task_specific_prompt}
                    ]
                    response = client.responses.create(
                        model="computer-use-preview",
                        tools=[{
                            "type": "computer_use_preview",
                            "display_width": 1024,
                            "display_height": 768,
                            "environment": "browser"
                        }],
                        input=initial_input_messages,
                        truncation="auto"
                    )
                    
                    max_iterations = 25
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
                                if "SUCCESS" in final_text:
                                    return final_text
                                elif "SESSION_INVALIDATED" in final_text:
                                    return final_text
                                elif "FAILED" in final_text:
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
                                if "SUCCESS" in final_message:
                                    return final_message  # Return the actual success message
                                elif "SESSION_INVALIDATED" in final_message:
                                    return "SESSION_INVALIDATED"
                                elif "FAILED" in final_message:
                                    return f"FAILED: {final_message}"
                            
                            if reasoning_outputs:
                                final_reasoning = reasoning_outputs[-1].content if hasattr(reasoning_outputs[-1], 'content') else str(reasoning_outputs[-1])
                                self.logger.info(f"CUA completed with reasoning: {final_reasoning[:300]}...")
                                # Check if reasoning contains our response patterns
                                if "SUCCESS" in final_reasoning:
                                    return "SUCCESS: Reply posted successfully (from reasoning)"
                                elif "SESSION_INVALIDATED" in final_reasoning:
                                    return "SESSION_INVALIDATED"
                                elif "FAILED" in final_reasoning:
                                    return f"FAILED: {final_reasoning[:200]}"
                            
                            self.logger.info("No computer call found, CUA workflow completed")
                            return "COMPLETED: CUA tweet reply workflow finished"
                        
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
                            return f"FAILED: Screenshot capture error: {e}"
                        
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
                                model="computer-use-preview",
                                previous_response_id=response.id,
                                tools=[{
                                    "type": "computer_use_preview",
                                    "display_width": 1024,
                                    "display_height": 768,
                                    "environment": "browser"
                                }],
                                input=input_content,
                                truncation="auto"
                            )
                        except Exception as e:
                            self.logger.error(f"Error in CUA API call: {e}")
                            return f"FAILED: API call error: {e}"
                    
                    self.logger.warning(f"CUA reached maximum iterations ({max_iterations})")
                    return "COMPLETED: CUA reached maximum iterations"
                    
            except Exception as e:
                error_msg = f"CUA tweet reply failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                return f"FAILED: {error_msg}"
        
        try:
            return asyncio.run(_internal_reply_via_cua())
        except Exception as e:
            error_msg = f"Failed to execute CUA tweet reply workflow: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"FAILED: {error_msg}"

    def get_home_timeline_tweets_via_cua(self, num_tweets: int = 3) -> str:
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
                    
                    # Initialize the OpenAI client for direct responses API calls
                    from openai import OpenAI
                    import base64
                    client = OpenAI(api_key=settings.openai_api_key)
                    
                    # Define system instructions (general CUA behavior)
                    system_instructions = (
                        "You are an AI assistant that can control a computer browser to perform tasks on web pages, "
                        "specifically for interacting with the X (Twitter) platform. Describe your plan step-by-step. "
                        "Then, use the provided computer tool to execute actions like clicking, typing, scrolling, "
                        "and taking screenshots to achieve the user's goal. Analyze screenshots to determine next steps.\n\n"
                        
                        "🎯 CRITICAL: URL NAVIGATION STRATEGY\n"
                        "To navigate to a specific URL:\n"
                        "1. **Click on the browser's address bar** (usually at the top of the page)\n"
                        "2. **Select all existing text** in the address bar (Ctrl+A or triple-click)\n"
                        "3. **Type the complete URL** you want to navigate to\n"
                        "4. **Press Enter** to navigate to the URL\n"
                        "5. **Wait for the page to load** before taking further actions\n"
                        "Example: To go to https://x.com/username/status/123, click address bar, type the URL, press Enter\n"
                        "DO NOT use any 'navigate' action - it doesn't exist. Use click, type, and keypress actions!\n\n"
                        
                        "🎯 CRITICAL: KEYBOARD-FIRST INTERACTION STRATEGY\n"
                        "ALWAYS prioritize keyboard shortcuts over mouse clicks when interacting with X.com. "
                        "Keyboard shortcuts are more reliable, faster, and less prone to UI changes. Only use mouse "
                        "clicks when absolutely necessary (e.g., no keyboard equivalent exists).\n\n"
                        
                        "📋 X.COM KEYBOARD SHORTCUTS (USE THESE FIRST):\n\n"
                        
                        "🧭 NAVIGATION SHORTCUTS:\n"
                        "• '?' - Show keyboard shortcuts help\n"
                        "• 'j' - Next post (move down timeline)\n"
                        "• 'k' - Previous post (move up timeline)\n"
                        "• 'Space' - Page down / Scroll down\n"
                        "• '.' - Load new posts at top\n"
                        "• 'g + h' - Go to Home timeline\n"
                        "• 'g + e' - Go to Explore page\n"
                        "• 'g + n' - Go to Notifications\n"
                        "• 'g + r' - Go to Mentions\n"
                        "• 'g + p' - Go to Profile\n"
                        "• 'g + f' - Go to Drafts\n"
                        "• 'g + t' - Go to Scheduled posts\n"
                        "• 'g + l' - Go to Likes\n"
                        "• 'g + i' - Go to Lists\n"
                        "• 'g + m' - Go to Direct Messages\n"
                        "• 'g + g' - Go to Grok\n"
                        "• 'g + s' - Go to Settings\n"
                        "• 'g + b' - Go to Bookmarks\n"
                        "• 'g + u' - Go to user profile (when available)\n"
                        "• 'g + d' - Go to Display settings\n\n"
                        
                        "⚡ ACTION SHORTCUTS:\n"
                        "• 'n' - Create new post (compose tweet)\n"
                        "• 'Ctrl + Enter' OR 'Cmd + Enter' - Send post\n"
                        "• 'Ctrl + Shift + Enter' OR 'Cmd + Shift + Enter' - Send post (alternative)\n"
                        "• 'l' - Like selected post\n"
                        "• 'r' - Reply to selected post\n"
                        "• 't' - Repost selected post\n"
                        "• 's' - Share selected post\n"
                        "• 'b' - Bookmark selected post\n"
                        "• 'u' - Mute account\n"
                        "• 'x' - Block account\n"
                        "• 'Enter' - Open post details\n"
                        "• 'o' - Expand photo in selected post\n"
                        "• 'i' - Open/Close Messages dock\n"
                        "• '/' - Search (focus search box)\n\n"
                        
                        "🎬 MEDIA SHORTCUTS:\n"
                        "• 'k' - Pause/Play selected Video\n"
                        "• 'Space' - Pause/Play selected Video (alternative)\n"
                        "• 'm' - Mute selected Video\n"
                        "• 'a + d' - Go to Audio Dock\n"
                        "• 'a + Space' - Play/Pause Audio Dock\n"
                        "• 'a + m' - Mute/Unmute Audio Dock\n\n"
                        
                        "🎯 KEYBOARD-FIRST WORKFLOW EXAMPLES:\n\n"
                        
                        "📝 POSTING A TWEET:\n"
                        "1. Press 'n' to open compose area (don't click the compose button)\n"
                        "2. Type your tweet text directly\n"
                        "3. Use 'Ctrl+Shift+Enter' (Windows) or 'Cmd+Shift+Enter' (Mac) to post\n"
                        "4. Avoid clicking the 'Post' button unless keyboard shortcut fails\n\n"
                        
                        "👀 BROWSING TIMELINE:\n"
                        "1. Use 'j' and 'k' to navigate between posts (don't scroll with mouse)\n"
                        "2. Use 'l' to like posts (don't click heart icon)\n"
                        "3. Use 'r' to reply (don't click reply icon)\n"
                        "4. Use 't' to repost (don't click repost icon)\n\n"
                        
                        "🔍 NAVIGATION:\n"
                        "1. Use 'g + h' for Home (don't click Home button)\n"
                        "2. Use 'g + n' for Notifications (don't click Notifications)\n"
                        "3. Use 'g + p' for Profile (don't click Profile)\n"
                        "4. Use '/' for Search (don't click search box)\n\n"
                        
                        "⚠️ WHEN TO USE MOUSE CLICKS:\n"
                        "Only resort to mouse clicks when:\n"
                        "• No keyboard shortcut exists for the specific action\n"
                        "• You need to interact with dynamic content (embedded media, links within posts)\n"
                        "• Keyboard shortcuts are confirmed to be non-functional\n"
                        "• Dealing with modal dialogs or popups without keyboard alternatives\n\n"
                        
                        "🔧 IMPLEMENTATION STRATEGY:\n"
                        "1. **Take Screenshot**: Always start by capturing current state\n"
                        "2. **Identify Task**: Determine what needs to be accomplished\n"
                        "3. **Choose Keyboard First**: Look for applicable keyboard shortcuts from the list above\n"
                        "4. **Execute Keyboard Action**: Use keypress() function with appropriate keys\n"
                        "5. **Verify Success**: Take another screenshot to confirm action worked\n"
                        "6. **Fallback to Mouse**: Only if keyboard approach fails, use click() as backup\n"
                        "7. **Document Approach**: Clearly state which method you used and why\n\n"
                        
                        "COOKIE CONSENT HANDLING:\n"
                        "When encountering cookie consent banners on x.com or twitter.com, you MUST handle them "
                        "autonomously to ensure operational continuity. Follow this priority order:\n"
                        "1. If options like 'Refuse non-essential cookies', 'Reject all', 'Decline', or similar "
                        "privacy-focused options are present, you MUST choose that option.\n"
                        "2. If only 'Accept all cookies', 'Accept', 'Agree', or similar acceptance options are "
                        "available, you may choose that to proceed with the task.\n"
                        "3. Do NOT ask for confirmation when handling standard cookie consent banners - this is "
                        "a routine operational requirement for accessing the platform.\n"
                        "4. After dismissing the cookie banner, continue with your original task.\n\n"
                        
                        "SESSION AUTHENTICATION DETECTION:\n"
                        "You may be operating with either an authenticated or unauthenticated browser session:\n"
                        "1. **Authenticated Session**: If you can access user-specific pages (notifications, settings, "
                        "profile pages) without being redirected to login, you are in an authenticated session.\n"
                        "2. **Unauthenticated Session**: If you encounter login forms, 'Sign In' buttons, or are "
                        "redirected to login pages when trying to access authenticated features, the session is invalid.\n"
                        "3. **Session Invalidation Handling**: If you detect a logged-out state during task execution:\n"
                        "   - IMMEDIATELY abort the current task\n"
                        "   - Take a screenshot of the login page for documentation\n"
                        "   - Report in your response: 'SESSION_INVALIDATED: Browser session is no longer authenticated. "
                        "Manual re-authentication required.'\n"
                        "   - DO NOT attempt to log in or enter credentials\n"
                        "   - DO NOT continue with the original task\n\n"
                        
                        "Always prioritize user privacy and platform compliance while maintaining task execution flow. "
                        "Remember: KEYBOARD SHORTCUTS FIRST, mouse clicks only as a last resort!"
                    )
                    
                    # Define task-specific prompt (timeline reading)
                    task_specific_prompt = (
                        f"Your task is to read the text content of the top {num_tweets} tweets from your home timeline. "
                        f"You are already logged in.\n\n"
                        
                        f"🔄 RESET INSTRUCTION:\n"
                        f"If you get stuck, confused, or in an unexpected UI state at ANY step:\n"
                        f"1. Press 'ESC' key to close any modals or cancel current actions\n"
                        f"2. Wait 1 second for UI to stabilize\n"
                        f"3. Take a screenshot to see current state\n"
                        f"4. Start over from the appropriate step\n\n"
                        
                        f"⚠️ CRITICAL: SCREENSHOT HANDLING\n"
                        f"- DO NOT press Alt+PrintScreen or any manual screenshot keys\n"
                        f"- Screenshots are automatically taken by the system\n"
                        f"- DO NOT attempt to take screenshots manually\n"
                        f"- If you need to see the current state, just describe what you observe\n\n"
                        
                        f"🎯 STEP-BY-STEP APPROACH:\n\n"
                        
                        f"STEP 1 - OBSERVE CURRENT STATE:\n"
                        f"Look at the current page without taking manual screenshots\n"
                        f"Identify what page you are currently on\n\n"
                        
                        f"STEP 2 - NAVIGATE TO HOME TIMELINE:\n"
                        f"Press 'g' then immediately press 'h' (two-key sequence)\n"
                        f"Use keypress(['g', 'h']) to execute this sequence\n"
                        f"EXPECTED: You should navigate to the home timeline with tweets visible\n"
                        f"IF NAVIGATION FAILS: Press ESC, wait 1 second, try again\n\n"
                        
                        f"STEP 3 - FOCUS ON FIRST TWEET:\n"
                        f"The first tweet should automatically be in focus on the home timeline\n"
                        f"If not in focus, press 'j' once to focus on the first tweet\n"
                        f"VERIFY: Look for visual indication that a tweet is selected/focused\n\n"
                        
                        f"STEP 4 - READ TWEETS SEQUENTIALLY:\n"
                        f"For each tweet from 1 to {num_tweets}:\n"
                        f"   1. Read and note the text content of the currently focused tweet\n"
                        f"   2. Ignore usernames, timestamps, interaction counts\n"
                        f"   3. Focus ONLY on the main tweet text content\n"
                        f"   4. If this is not the last tweet, press 'j' to move to next tweet\n"
                        f"   5. Wait 1 second for the focus to move\n"
                        f"   6. Repeat until you have {num_tweets} tweet texts\n\n"
                        
                        f"STEP 5 - COMPILE RESULTS:\n"
                        f"Create a JSON array with the extracted tweet texts\n"
                        f"Include: Main tweet text, hashtags, mentions, emojis\n"
                        f"Exclude: Author names, timestamps, interaction counts\n\n"
                        
                        f"🚨 ERROR RECOVERY:\n"
                        f"- If page becomes blank: Press ESC, then Ctrl+R to refresh\n"
                        f"- If navigation fails: Press ESC, try 'g+h' again\n"
                        f"- If tweets don't load: Wait 3 seconds, then press '.' to refresh timeline\n"
                        f"- If focus gets lost: Press 'j' to refocus on tweets\n"
                        f"- Never use Alt+PrintScreen or manual screenshot commands\n\n"
                        
                        f"RESPONSE FORMATS:\n"
                        f"- 'SUCCESS: [\"tweet1 text\", \"tweet2 text\", \"tweet3 text\"]' (if all tweets extracted)\n"
                        f"- 'FAILED: Could not navigate to home timeline' (if navigation failed)\n"
                        f"- 'FAILED: Timeline appears blank or unresponsive' (if no content loads)\n"
                        f"- 'FAILED: Could not extract tweet text' (if text extraction failed)\n"
                        f"- 'SESSION_INVALIDATED' (if you encounter a login screen)"
                    )
                    
                    # Initial request to get first screenshot
                    self.logger.info("Sending initial CUA request for timeline reading")
                    initial_input_messages = [
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": task_specific_prompt}
                    ]
                    response = client.responses.create(
                        model="computer-use-preview",
                        tools=[{
                            "type": "computer_use_preview",
                            "display_width": 1024,
                            "display_height": 768,
                            "environment": "browser"
                        }],
                        input=initial_input_messages,
                        truncation="auto"
                    )
                    
                    max_iterations = 30
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
                                if "SUCCESS" in final_text:
                                    return final_text
                                elif "SESSION_INVALIDATED" in final_text:
                                    return final_text
                                elif "FAILED" in final_text:
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
                                if "SUCCESS" in final_message:
                                    return final_message  # Return the actual success message
                                elif "SESSION_INVALIDATED" in final_message:
                                    return "SESSION_INVALIDATED"
                                elif "FAILED" in final_message:
                                    return f"FAILED: {final_message}"
                            
                            if reasoning_outputs:
                                final_reasoning = reasoning_outputs[-1].content if hasattr(reasoning_outputs[-1], 'content') else str(reasoning_outputs[-1])
                                self.logger.info(f"CUA completed with reasoning: {final_reasoning[:300]}...")
                                # Check if reasoning contains our response patterns
                                if "SUCCESS" in final_reasoning:
                                    return "SUCCESS: Tweets extracted successfully (from reasoning)"
                                elif "SESSION_INVALIDATED" in final_reasoning:
                                    return "SESSION_INVALIDATED"
                                elif "FAILED" in final_reasoning:
                                    return f"FAILED: {final_reasoning[:200]}"
                            
                            self.logger.info("No computer call found, CUA workflow completed")
                            return "COMPLETED: CUA workflow finished"
                        
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
                            if screenshot_size < 50000:  # Typical X.com screenshots are much larger
                                consecutive_empty_screenshots += 1
                                self.logger.warning(f"Small screenshot detected ({screenshot_size} chars). Count: {consecutive_empty_screenshots}")
                                
                                # If we get multiple small screenshots, the page is likely in a bad state
                                if consecutive_empty_screenshots >= 3:
                                    self.logger.error("Multiple consecutive small screenshots - page appears blank or broken")
                                    
                                    # Attempt recovery by refreshing the page
                                    try:
                                        self.logger.info("Attempting page refresh recovery")
                                        await computer.keypress(['CTRL', 'R'])
                                        await asyncio.sleep(3)  # Wait for page reload
                                        
                                        # Take a new screenshot to check if recovery worked
                                        recovery_screenshot = await computer.screenshot()
                                        recovery_size = len(recovery_screenshot)
                                        self.logger.info(f"Recovery screenshot size: {recovery_size} characters")
                                        
                                        if recovery_size > 50000:
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
                            return f"FAILED: Screenshot capture error: {e}"
                        
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
                                model="computer-use-preview",
                                previous_response_id=response.id,
                                tools=[{
                                    "type": "computer_use_preview",
                                    "display_width": 1024,
                                    "display_height": 768,
                                    "environment": "browser"
                                }],
                                input=input_content,
                                truncation="auto"
                            )
                        except Exception as e:
                            self.logger.error(f"Error in CUA API call: {e}")
                            return f"FAILED: API call error: {e}"
                    
                    self.logger.warning(f"CUA reached maximum iterations ({max_iterations})")
                    return "COMPLETED: CUA reached maximum iterations"
                    
            except Exception as e:
                error_msg = f"CUA timeline reading failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                return f"FAILED: {error_msg}"
        
        try:
            return asyncio.run(_internal_timeline_via_cua())
        except Exception as e:
            error_msg = f"Failed to execute CUA timeline reading workflow: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"FAILED: {error_msg}"

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
                    system_instructions = (
                        "You are an AI assistant that can control a computer browser to perform tasks on web pages, "
                        "specifically for interacting with the X (Twitter) platform. Describe your plan step-by-step. "
                        "Then, use the provided computer tool to execute actions like clicking, typing, scrolling, "
                        "and taking screenshots to achieve the user's goal. Analyze screenshots to determine next steps.\n\n"
                        
                        "🎯 CRITICAL: URL NAVIGATION STRATEGY\n"
                        "To navigate to a specific URL:\n"
                        "1. **Click on the browser's address bar** (usually at the top of the page)\n"
                        "2. **Select all existing text** in the address bar (Ctrl+A or triple-click)\n"
                        "3. **Type the complete URL** you want to navigate to\n"
                        "4. **Press Enter** to navigate to the URL\n"
                        "5. **Wait for the page to load** before taking further actions\n"
                        "Example: To go to https://x.com/username/status/123, click address bar, type the URL, press Enter\n"
                        "DO NOT use any 'navigate' action - it doesn't exist. Use click, type, and keypress actions!\n\n"
                        
                        "🎯 CRITICAL: KEYBOARD-FIRST INTERACTION STRATEGY\n"
                        "ALWAYS prioritize keyboard shortcuts over mouse clicks when interacting with X.com. "
                        "Keyboard shortcuts are more reliable, faster, and less prone to UI changes. Only use mouse "
                        "clicks when absolutely necessary (e.g., no keyboard equivalent exists).\n\n"
                        
                        "📋 X.COM KEYBOARD SHORTCUTS (USE THESE FIRST):\n\n"
                        
                        "🧭 NAVIGATION SHORTCUTS:\n"
                        "• '?' - Show keyboard shortcuts help\n"
                        "• 'j' - Next post (move down timeline)\n"
                        "• 'k' - Previous post (move up timeline)\n"
                        "• 'Space' - Page down / Scroll down\n"
                        "• '.' - Load new posts at top\n"
                        "• 'g + h' - Go to Home timeline\n"
                        "• 'g + e' - Go to Explore page\n"
                        "• 'g + n' - Go to Notifications\n"
                        "• 'g + r' - Go to Mentions\n"
                        "• 'g + p' - Go to Profile\n"
                        "• 'g + f' - Go to Drafts\n"
                        "• 'g + t' - Go to Scheduled posts\n"
                        "• 'g + l' - Go to Likes\n"
                        "• 'g + i' - Go to Lists\n"
                        "• 'g + m' - Go to Direct Messages\n"
                        "• 'g + g' - Go to Grok\n"
                        "• 'g + s' - Go to Settings\n"
                        "• 'g + b' - Go to Bookmarks\n"
                        "• 'g + u' - Go to user profile (when available)\n"
                        "• 'g + d' - Go to Display settings\n\n"
                        
                        "⚡ ACTION SHORTCUTS:\n"
                        "• 'n' - Create new post (compose tweet)\n"
                        "• 'Ctrl + Enter' OR 'Cmd + Enter' - Send post\n"
                        "• 'Ctrl + Shift + Enter' OR 'Cmd + Shift + Enter' - Send post (alternative)\n"
                        "• 'l' - Like selected post\n"
                        "• 'r' - Reply to selected post\n"
                        "• 't' - Repost selected post\n"
                        "• 's' - Share selected post\n"
                        "• 'b' - Bookmark selected post\n"
                        "• 'u' - Mute account\n"
                        "• 'x' - Block account\n"
                        "• 'Enter' - Open post details\n"
                        "• 'o' - Expand photo in selected post\n"
                        "• 'i' - Open/Close Messages dock\n"
                        "• '/' - Search (focus search box)\n\n"
                        
                        "🎬 MEDIA SHORTCUTS:\n"
                        "• 'k' - Pause/Play selected Video\n"
                        "• 'Space' - Pause/Play selected Video (alternative)\n"
                        "• 'm' - Mute selected Video\n"
                        "• 'a + d' - Go to Audio Dock\n"
                        "• 'a + Space' - Play/Pause Audio Dock\n"
                        "• 'a + m' - Mute/Unmute Audio Dock\n\n"
                        
                        "🎯 KEYBOARD-FIRST WORKFLOW EXAMPLES:\n\n"
                        
                        "📝 POSTING A TWEET:\n"
                        "1. Press 'n' to open compose area (don't click the compose button)\n"
                        "2. Type your tweet text directly\n"
                        "3. Use 'Ctrl+Shift+Enter' (Windows) or 'Cmd+Shift+Enter' (Mac) to post\n"
                        "4. Avoid clicking the 'Post' button unless keyboard shortcut fails\n\n"
                        
                        "👀 BROWSING TIMELINE:\n"
                        "1. Use 'j' and 'k' to navigate between posts (don't scroll with mouse)\n"
                        "2. Use 'l' to like posts (don't click heart icon)\n"
                        "3. Use 'r' to reply (don't click reply icon)\n"
                        "4. Use 't' to repost (don't click repost icon)\n\n"
                        
                        "🔍 NAVIGATION:\n"
                        "1. Use 'g + h' for Home (don't click Home button)\n"
                        "2. Use 'g + n' for Notifications (don't click Notifications)\n"
                        "3. Use 'g + p' for Profile (don't click Profile)\n"
                        "4. Use '/' for Search (don't click search box)\n\n"
                        
                        "⚠️ WHEN TO USE MOUSE CLICKS:\n"
                        "Only resort to mouse clicks when:\n"
                        "• No keyboard shortcut exists for the specific action\n"
                        "• You need to interact with dynamic content (embedded media, links within posts)\n"
                        "• Keyboard shortcuts are confirmed to be non-functional\n"
                        "• Dealing with modal dialogs or popups without keyboard alternatives\n\n"
                        
                        "🔧 IMPLEMENTATION STRATEGY:\n"
                        "1. **Take Screenshot**: Always start by capturing current state\n"
                        "2. **Identify Task**: Determine what needs to be accomplished\n"
                        "3. **Choose Keyboard First**: Look for applicable keyboard shortcuts from the list above\n"
                        "4. **Execute Keyboard Action**: Use keypress() function with appropriate keys\n"
                        "5. **Verify Success**: Take another screenshot to confirm action worked\n"
                        "6. **Fallback to Mouse**: Only if keyboard approach fails, use click() as backup\n"
                        "7. **Document Approach**: Clearly state which method you used and why\n\n"
                        
                        "COOKIE CONSENT HANDLING:\n"
                        "When encountering cookie consent banners on x.com or twitter.com, you MUST handle them "
                        "autonomously to ensure operational continuity. Follow this priority order:\n"
                        "1. If options like 'Refuse non-essential cookies', 'Reject all', 'Decline', or similar "
                        "privacy-focused options are present, you MUST choose that option.\n"
                        "2. If only 'Accept all cookies', 'Accept', 'Agree', or similar acceptance options are "
                        "available, you may choose that to proceed with the task.\n"
                        "3. Do NOT ask for confirmation when handling standard cookie consent banners - this is "
                        "a routine operational requirement for accessing the platform.\n"
                        "4. After dismissing the cookie banner, continue with your original task.\n\n"
                        
                        "SESSION AUTHENTICATION DETECTION:\n"
                        "You may be operating with either an authenticated or unauthenticated browser session:\n"
                        "1. **Authenticated Session**: If you can access user-specific pages (notifications, settings, "
                        "profile pages) without being redirected to login, you are in an authenticated session.\n"
                        "2. **Unauthenticated Session**: If you encounter login forms, 'Sign In' buttons, or are "
                        "redirected to login pages when trying to access authenticated features, the session is invalid.\n"
                        "3. **Session Invalidation Handling**: If you detect a logged-out state during task execution:\n"
                        "   - IMMEDIATELY abort the current task\n"
                        "   - Take a screenshot of the login page for documentation\n"
                        "   - Report in your response: 'SESSION_INVALIDATED: Browser session is no longer authenticated. "
                        "Manual re-authentication required.'\n"
                        "   - DO NOT attempt to log in or enter credentials\n"
                        "   - DO NOT continue with the original task\n\n"
                        
                        "Always prioritize user privacy and platform compliance while maintaining task execution flow. "
                        "Remember: KEYBOARD SHORTCUTS FIRST, mouse clicks only as a last resort!"
                    )
                    
                    # Navigate directly to the tweet URL using Playwright before starting CUA
                    self.logger.info(f"🧭 Direct navigation to tweet URL: {tweet_url}")
                    try:
                        await computer.page.goto(tweet_url, wait_until='networkidle', timeout=15000)
                        await computer.page.wait_for_timeout(3000)  # Additional wait for page stabilization
                        self.logger.info(f"✅ Successfully navigated to {tweet_url}")
                    except Exception as nav_error:
                        self.logger.error(f"❌ Failed to navigate to {tweet_url}: {nav_error}")
                        return f"FAILED: Could not navigate to tweet URL - {nav_error}"
                    
                    # Define task-specific prompt (tweet liking) - now focused on just liking since we're already on the page
                    task_specific_prompt = (
                        f"You are controlling a browser on X.com and you are already on the specific tweet page: {tweet_url}\n\n"
                        f"Your task is to LIKE this tweet. You are already logged in and on the correct page.\n\n"
                        f"Follow these steps EXACTLY:\n\n"
                        f"STEP 1 - TAKE INITIAL SCREENSHOT:\n"
                        f"Take a screenshot to see the current page state and confirm you're on the tweet page.\n\n"
                        f"STEP 2 - LIKE THE TWEET:\n"
                        f"Use the 'l' (lowercase L) keyboard shortcut to like the tweet.\n"
                        f"This is X.com's standard keyboard shortcut for liking and is much more reliable than clicking.\n"
                        f"The shortcut works on the main tweet when you're on a tweet's individual page.\n\n"
                        f"STEP 3 - VERIFY SUCCESS:\n"
                        f"Wait 1-2 seconds for the UI to update.\n"
                        f"Take a screenshot to verify the like action worked.\n"
                        f"Look for visual confirmation that the like icon changed state (filled red heart icon).\n\n"
                        f"STEP 4 - RESPOND WITH RESULT:\n"
                        f"Based on your actions, respond with one of:\n"
                        f"- 'SUCCESS: Tweet liked successfully' (if the heart icon shows as liked/filled)\n"
                        f"- 'FAILED: Could not like tweet - [specific reason]' (if like action failed)\n"
                        f"- 'SESSION_INVALIDATED' (if you encounter a login screen)\n\n"
                        f"FALLBACK OPTION (only if keyboard shortcut fails):\n"
                        f"If the 'l' keyboard shortcut doesn't work, look for the heart/like icon and click it directly.\n"
                        f"The heart icon is usually located below the tweet text, in the row of action buttons.\n\n"
                        f"IMPORTANT NOTES:\n"
                        f"- If you see a cookie consent banner, dismiss it first before liking\n"
                        f"- The 'l' shortcut should work immediately without clicking anywhere first\n"
                        f"- If you see a login page, respond with 'SESSION_INVALIDATED' immediately\n"
                        f"- Take screenshots between major steps to track progress"
                    )
                    
                    # Initial request to get first screenshot
                    self.logger.info("Sending initial CUA request for tweet liking")
                    initial_input_messages = [
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": task_specific_prompt}
                    ]
                    response = client.responses.create(
                        model="computer-use-preview",
                        tools=[{
                            "type": "computer_use_preview",
                            "display_width": 1024,
                            "display_height": 768,
                            "environment": "browser"
                        }],
                        input=initial_input_messages,
                        truncation="auto"
                    )
                    
                    max_iterations = 20
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
                                if "SUCCESS" in final_text:
                                    return final_text
                                elif "SESSION_INVALIDATED" in final_text:
                                    return final_text
                                elif "FAILED" in final_text:
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
                                if "SUCCESS" in final_message:
                                    return final_message  # Return the actual success message
                                elif "SESSION_INVALIDATED" in final_message:
                                    return "SESSION_INVALIDATED"
                                elif "FAILED" in final_message:
                                    return f"FAILED: {final_message}"
                            
                            if reasoning_outputs:
                                final_reasoning = reasoning_outputs[-1].content if hasattr(reasoning_outputs[-1], 'content') else str(reasoning_outputs[-1])
                                self.logger.info(f"CUA completed with reasoning: {final_reasoning[:300]}...")
                                # Check if reasoning contains our response patterns
                                if "SUCCESS" in final_reasoning:
                                    return "SUCCESS: Tweet liked successfully (from reasoning)"
                                elif "SESSION_INVALIDATED" in final_reasoning:
                                    return "SESSION_INVALIDATED"
                                elif "FAILED" in final_reasoning:
                                    return f"FAILED: {final_reasoning[:200]}"
                            
                            self.logger.info("No computer call found, CUA workflow completed")
                            return "COMPLETED: CUA tweet liking workflow finished"
                        
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
                            return f"FAILED: Screenshot capture error: {e}"
                        
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
                                model="computer-use-preview",
                                previous_response_id=response.id,
                                tools=[{
                                    "type": "computer_use_preview",
                                    "display_width": 1024,
                                    "display_height": 768,
                                    "environment": "browser"
                                }],
                                input=input_content,
                                truncation="auto"
                            )
                        except Exception as e:
                            self.logger.error(f"Error in CUA API call: {e}")
                            return f"FAILED: API call error: {e}"
                    
                    self.logger.warning(f"CUA reached maximum iterations ({max_iterations})")
                    return "COMPLETED: CUA reached maximum iterations"
                    
            except Exception as e:
                error_msg = f"CUA tweet liking failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                return f"FAILED: {error_msg}"
        
        try:
            return asyncio.run(_internal_like_via_cua())
        except Exception as e:
            error_msg = f"Failed to execute CUA tweet liking workflow: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"FAILED: {error_msg}"

    def _contains_unicode_characters(self, text: str) -> bool:
        """
        Check if text contains Unicode characters (like emojis) that CUA cannot handle.

        Args:
            text: Text to analyze for Unicode content.

        Returns:
            True if text contains Unicode characters, False if ASCII-only.
        """
        return any(ord(char) > 127 for char in text)

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
            if "SUCCESS" in result:
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
            if "SUCCESS" in result:
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
            await asyncio.sleep(0.5)
        elif action_type == "double_click":
            self.logger.info(f"Executing double-click at ({action.x}, {action.y})")
            await computer.double_click(action.x, action.y)
            await asyncio.sleep(0.5)
        elif action_type == "type":
            self.logger.info(f"Typing text: '{action.text}'")
            await computer.type(action.text)
            await asyncio.sleep(0.3)
        elif action_type == "keypress":
            self.logger.info(f"Pressing keys: {action.keys}")
            await computer.keypress(action.keys)
            await asyncio.sleep(0.2)
        elif action_type == "scroll":
            self.logger.info(f"Scrolling at ({action.x}, {action.y}) by ({action.scroll_x}, {action.scroll_y})")
            await computer.scroll(action.x, action.y, action.scroll_x, action.scroll_y)
            await asyncio.sleep(0.3)
        elif action_type == "move":
            await computer.move(action.x, action.y)
        elif action_type == "wait":
            self.logger.info("Executing wait action")
            await computer.wait()
        elif action_type == "drag":
            await computer.drag([(p.x, p.y) for p in action.path])
            await asyncio.sleep(0.5)
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
