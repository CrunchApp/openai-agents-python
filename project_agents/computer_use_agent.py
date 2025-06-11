"""
Module defining a ComputerUseAgent that uses the ComputerTool for CUA tasks.
"""

import logging

from agents import Agent, ModelSettings, function_tool, RunContextWrapper
from core.cua_workflow import CuaWorkflowRunner
from core.models import CuaTask
from typing import Any


class ComputerUseAgent(Agent):
    """Agent that controls a browser via the ComputerTool for X (Twitter) platform interactions."""

    def __init__(self) -> None:
        """Initialize the ComputerUseAgent with browser control capabilities."""
        self.logger = logging.getLogger(__name__)
        
        super().__init__(
            name="Computer Use Agent",
            instructions=(
                """
                You are the **Computer Use Agent** (CUA) for AIified.

                ROLE: Execute browser-based workflows on X (Twitter) exactly as instructed via structured CuaTask objects.

                WHEN A HANDOFF ARRIVES:
                • If a `CuaTask` object is present, run `execute_cua_task` immediately and return its result.
                • If natural language instructions are given instead, politely explain that you require a structured CuaTask and suggest using `create_smart_cua_task`.

                BEST PRACTICES:
                • Never perform actions outside the task scope.
                • Keep human-session authentic; avoid hard-coded waits – rely on the task prompt.
                • Return only the task result or error message, nothing else.
                """
            ),
            model="computer-use-preview", 
            model_settings=ModelSettings(truncation="auto"),
            tools=[],  # No ComputerTool - we handle CUA tasks through structured workflow
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
        
        This method creates a single-use CUA session for backward compatibility.
        For persistent sessions, use CuaSessionManager directly.
        
        Args:
            task: The CuaTask object containing prompt, start_url, and configuration
            
        Returns:
            String describing the outcome of the CUA operation
        """
        self.logger.info(f"ComputerUseAgent executing structured task: {task.prompt[:100]}...")
        
        try:
            # Import here to avoid circular dependency
            from core.cua_session_manager import CuaSessionManager
            
            # Use session manager for proper lifecycle management
            async with CuaSessionManager() as session:
                result = await session.run_task(task)
                
            self.logger.info(f"CUA task completed with result: {result[:200]}...")
            return result
        except Exception as e:
            error_msg = f"CUA task execution failed: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"FAILED: {error_msg}" 