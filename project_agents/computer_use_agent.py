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
                "and taking screenshots to achieve the user's goal. Analyze screenshots to determine next steps."
            ),
            model="computer-use-preview",
            model_settings=ModelSettings(truncation="auto"),
            tools=[ComputerTool(computer=self.computer)],
        )
        self.logger = logging.getLogger(__name__) 