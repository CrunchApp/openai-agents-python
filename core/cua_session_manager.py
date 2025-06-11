"""CUA Session Manager for persistent browser automation sessions.

This module provides the CuaSessionManager class that manages the lifecycle
of a single, long-lived LocalPlaywrightComputer instance for efficient
stateful CUA operations.

The session manager enables multiple sequential CUA tasks to be executed
within the same browser session, eliminating the overhead of repeatedly
starting and stopping browser instances.
"""

import logging
from typing import Optional

from core.computer_env.local_playwright_computer import LocalPlaywrightComputer
from core.cua_workflow import CuaWorkflowRunner
from core.models import CuaTask
from core.config import settings


class CuaSessionManager:
    """Manages the lifecycle of a persistent CUA browser session.
    
    This class enables efficient stateful CUA operations by maintaining
    a single browser session across multiple tasks, rather than creating
    a new session for each individual task.
    
    Usage:
        async with CuaSessionManager() as session:
            result1 = await session.run_task(task1)
            result2 = await session.run_task(task2)
            # Browser stays open between tasks
    """
    
    def __init__(self, user_data_dir_path: Optional[str] = None) -> None:
        """Initialize the CUA session manager.
        
        Args:
            user_data_dir_path: Optional path to persistent browser user data directory.
                              If None, uses the configured X CUA user data directory.
        """
        self.logger = logging.getLogger(__name__)
        self.computer: Optional[LocalPlaywrightComputer] = None
        self.user_data_dir_path = user_data_dir_path or settings.x_cua_user_data_dir
        self._session_started = False
    
    async def __aenter__(self) -> "CuaSessionManager":
        """Enter context manager: start the persistent CUA session.
        
        Returns:
            Self instance with initialized computer session
            
        Raises:
            Exception: If session initialization fails
        """
        self.logger.info("🚀 Starting persistent CUA session...")
        
        try:
            # Create and initialize the computer instance
            self.computer = LocalPlaywrightComputer(
                user_data_dir_path=self.user_data_dir_path
            )
            
            # Start the computer session (browser + page initialization)
            await self.computer.__aenter__()
            
            self._session_started = True
            self.logger.info("✅ Persistent CUA session started successfully")
            
            return self
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start CUA session: {e}", exc_info=True)
            # Cleanup on failure
            if self.computer:
                try:
                    await self.computer.__aexit__(None, None, None)
                except Exception as cleanup_error:
                    self.logger.error(f"Error during cleanup: {cleanup_error}")
                self.computer = None
            raise Exception(f"CUA session initialization failed: {e}")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager: safely close the persistent CUA session.
        
        Args:
            exc_type: Exception type if any
            exc_val: Exception value if any  
            exc_tb: Exception traceback if any
        """
        self.logger.info("🛑 Stopping persistent CUA session...")
        
        if self.computer and self._session_started:
            try:
                await self.computer.__aexit__(exc_type, exc_val, exc_tb)
                self.logger.info("✅ CUA session stopped successfully")
            except Exception as e:
                self.logger.error(f"❌ Error stopping CUA session: {e}", exc_info=True)
            finally:
                self.computer = None
                self._session_started = False
        else:
            self.logger.info("ℹ️ No active CUA session to stop")
    
    async def run_task(self, task: CuaTask) -> str:
        """Execute a CUA task within the persistent session.
        
        Args:
            task: The CuaTask object containing prompt, start_url, and configuration
            
        Returns:
            String describing the outcome of the CUA operation
            
        Raises:
            Exception: If session is not started or task execution fails
        """
        if not self._session_started or not self.computer:
            raise Exception("CUA session not started. Use async context manager.")
        
        self.logger.info(f"📋 Executing CUA task in persistent session: {task.prompt[:100]}...")
        
        try:
            # Use the stateless workflow runner with our persistent computer session
            runner = CuaWorkflowRunner()
            result = await runner.run_workflow(task, self.computer)
            
            self.logger.info(f"✅ CUA task completed: {result[:200]}...")
            return result
            
        except Exception as e:
            error_msg = f"CUA task execution failed in persistent session: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"FAILED: {error_msg}"
    
    @property
    def is_active(self) -> bool:
        """Check if the CUA session is currently active.
        
        Returns:
            True if session is started and computer is available
        """
        return self._session_started and self.computer is not None
    
    async def get_session_info(self) -> dict:
        """Get information about the current session state.
        
        Returns:
            Dictionary containing session state information
        """
        info = {
            "session_started": self._session_started,
            "computer_available": self.computer is not None,
            "user_data_dir": self.user_data_dir_path,
        }
        
        if self.computer and self._session_started:
            try:
                # Get current page URL if available
                current_url = await self.computer.page.url
                info["current_url"] = current_url
                info["page_title"] = await self.computer.page.title()
            except Exception as e:
                self.logger.warning(f"Could not get session info: {e}")
                info["session_error"] = str(e)
        
        return info 