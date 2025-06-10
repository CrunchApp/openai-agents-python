"""Data models for the X Agentic Unit project."""

from typing import Optional
from pydantic import BaseModel


class CuaTask(BaseModel):
    """A structured task for the ComputerUseAgent.
    
    This model defines the interface for handing off browser automation tasks
    to the ComputerUseAgent through the SDK's handoff mechanism.
    """
    prompt: str
    start_url: Optional[str] = None
    max_iterations: int = 30 