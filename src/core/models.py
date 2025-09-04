"""
Core models for Straussome orchestration system
"""

from typing import Any, Dict
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentResult:
    """Result from agent execution"""
    agent_id: str
    task_id: str
    status: AgentStatus
    result: Any = None
    error: str = None
    execution_time: float = 0.0
    retry_count: int = 0
    metadata: Dict[str, Any] = None


@dataclass
class TaskConfig:
    """Configuration for task execution"""
    timeout: float = 300.0  # 5 minutes default
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    concurrent_agents: int = 5


class AgentState(BaseModel):
    """Shared state for agent execution"""
    task_id: str
    agent_results: Dict[str, AgentResult] = Field(default_factory=dict)
    shared_data: Dict[str, Any] = Field(default_factory=dict)
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True
