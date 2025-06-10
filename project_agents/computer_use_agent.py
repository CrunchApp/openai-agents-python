"""
Module defining a ComputerUseAgent that uses the ComputerTool for CUA tasks.
"""

import logging

from agents import Agent, ModelSettings, ComputerTool, function_tool, RunContextWrapper
from core.computer_env.local_playwright_computer import LocalPlaywrightComputer
from core.config import settings
from core.cua_workflow import CuaWorkflowRunner
from core.models import CuaTask
from typing import Any


class ComputerUseAgent(Agent):
    """Agent that controls a browser via the ComputerTool for X (Twitter) platform interactions."""

    def __init__(self) -> None:
        """Initialize the ComputerUseAgent with browser control capabilities."""
        self.logger = logging.getLogger(__name__)
        
        # Initialize the computer environment
        self.computer = LocalPlaywrightComputer(user_data_dir_path=settings.x_cua_user_data_dir)
        
        super().__init__(
            name="Computer Use Agent",
            instructions=(
                "You are a Computer Use Agent that executes browser automation tasks for X (Twitter) platform interactions. "
                "When you receive a handoff, check if there's a structured CuaTask in the context. If so, use the "
                "execute_cua_task tool to handle it. Otherwise, use the computer tool to respond to natural language instructions."
                
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
            ),
            model="computer-use-preview",
            model_settings=ModelSettings(truncation="auto"),
            tools=[ComputerTool(computer=self.computer)],
        )
        
        # Add the execute_cua_task tool to handle structured CuaTask objects
        @function_tool(
            name_override="execute_cua_task", 
            description_override="Executes a structured CUA task using the centralized workflow runner."
        )
        async def _execute_cua_task_tool(ctx: RunContextWrapper[Any], task: CuaTask) -> str:
            """Tool wrapper for structured CUA task execution."""
            return await self.execute_cua_task(task)
        
        self.tools.append(_execute_cua_task_tool)
    
    async def execute_cua_task(self, task: CuaTask) -> str:
        """Execute a structured CUA task using the centralized workflow runner.
        
        Args:
            task: The CuaTask object containing prompt, start_url, and configuration
            
        Returns:
            String describing the outcome of the CUA operation
        """
        self.logger.info(f"ComputerUseAgent executing structured task: {task.prompt[:100]}...")
        
        try:
            runner = CuaWorkflowRunner()
            result = await runner.run_workflow(task)
            self.logger.info(f"CUA task completed with result: {result[:200]}...")
            return result
        except Exception as e:
            error_msg = f"CUA task execution failed: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"FAILED: {error_msg}" 