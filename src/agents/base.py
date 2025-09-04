from typing import Any, Dict, Optional
import logging
from ..core.models import AgentState


class BaseAgent:
    """Base class for all agents"""
    
    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None, tool_registry=None):
        self.agent_id = agent_id
        self.config = config or {}
        self.tool_registry = tool_registry
        self.logger = logging.getLogger(f"agent.{agent_id}")
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the agent's main logic"""
        raise NotImplementedError("Subclasses must implement execute method")
    
    def get_tool(self, tool_name: str):
        """Get a tool from the registry"""
        if self.tool_registry:
            return self.tool_registry.get_tool(tool_name)
        return None
