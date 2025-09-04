"""
Straussome API Package

This package contains the FastAPI application, routes, and API models.
"""

from .app import app
from .routes import router
from .models import (
    TaskConfigRequest,
    CreateTaskRequest,
    ToolExecuteRequest,
    AgentResultResponse,
    TaskStatusResponse,
    TaskResultResponse,
    ToolResultResponse,
    ErrorResponse,
    HealthResponse
)

__all__ = [
    # FastAPI app
    "app",
    "router",
    
    # Request models
    "TaskConfigRequest",
    "CreateTaskRequest",
    "ToolExecuteRequest",
    
    # Response models
    "AgentResultResponse",
    "TaskStatusResponse", 
    "TaskResultResponse",
    "ToolResultResponse",
    "ErrorResponse",
    "HealthResponse"
]
