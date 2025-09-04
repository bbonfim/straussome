"""
Pydantic models for API requests and responses
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from ..core.models import AgentStatus, TaskStatus, AgentResult, TaskConfig


# Request Models
class TaskConfigRequest(BaseModel):
    """Configuration for task execution"""
    timeout: float = Field(default=300.0, description="Task timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    retry_delay: float = Field(default=1.0, description="Initial retry delay in seconds")
    retry_backoff: float = Field(default=2.0, description="Retry backoff multiplier")
    concurrent_agents: int = Field(default=5, description="Maximum concurrent agents")


class CreateTaskRequest(BaseModel):
    """Request to create a new task"""
    agent_sequence: List[str] = Field(description="List of agent IDs to execute in sequence")
    initial_data: Optional[Dict[str, Any]] = Field(default=None, description="Initial data for agents")
    config: Optional[TaskConfigRequest] = Field(default=None, description="Task configuration")


class ToolExecuteRequest(BaseModel):
    """Request to execute a tool directly"""
    tool_name: str = Field(description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(description="Parameters for tool execution")


# Response Models
class AgentResultResponse(BaseModel):
    """Agent execution result"""
    agent_id: str
    status: AgentStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    retry_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskStatusResponse(BaseModel):
    """Task status response"""
    task_id: str
    status: TaskStatus
    agent_results: Dict[str, AgentResultResponse] = Field(default_factory=dict)
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TaskResultResponse(BaseModel):
    """Complete task result"""
    task_id: str
    status: TaskStatus
    agent_results: Dict[str, AgentResultResponse] = Field(default_factory=dict)
    shared_data: Dict[str, Any] = Field(default_factory=dict)
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)
    total_execution_time: float = 0.0


class ToolResultResponse(BaseModel):
    """Tool execution result"""
    tool_name: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    task_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str
    available_agents: List[str]
    available_tools: List[str]


class AgentInfo(BaseModel):
    """Agent information"""
    agent_id: str
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class ToolInfo(BaseModel):
    """Tool information"""
    tool_name: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
