"""
Module defining a ComputerUseAgent that uses the ComputerTool for CUA tasks.
"""

import logging

from agents import Agent, ModelSettings, ComputerTool
from core.computer_env.local_playwright_computer import LocalPlaywrightComputer
from core.computer_env.base import AsyncComputer


class ComputerUseAgent(Agent):
    """Agent that controls a browser via the ComputerTool to perform web-based tasks."""

    def __init__(self, computer: AsyncComputer) -> None:
        """
        Initialize the ComputerUseAgent with a given AsyncComputer implementation.

        Args:
            computer: An AsyncComputer implementation for GUI control.
        """
        self.computer = computer
        super().__init__(
            name="Computer Use Agent",
            instructions=(
                "You are an AI assistant that can control a computer browser to perform tasks on web pages, "
                "specifically for interacting with the X (Twitter) platform. Describe your plan step-by-step. "
                "Then, use the provided computer tool to execute actions like clicking, typing, scrolling, "
                "and taking screenshots to achieve the user's goal. Analyze screenshots to determine next steps.\n\n"
                
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
                
                "Always prioritize user privacy and platform compliance while maintaining task execution flow."
            ),
            model="computer-use-preview",
            model_settings=ModelSettings(truncation="auto"),
            tools=[ComputerTool(computer=self.computer)],
        )
        self.logger = logging.getLogger(__name__) 