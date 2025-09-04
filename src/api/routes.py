"""
FastAPI routes for the agent orchestrator
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

from .models import (
    CreateTaskRequest, TaskResultResponse, TaskStatusResponse, TaskConfigRequest,
    ToolExecuteRequest, ToolResultResponse, ErrorResponse, HealthResponse,
    AgentInfo, ToolInfo, TaskStatus, AgentStatus, AgentResultResponse
)
from ..core.orchestrator import AgentOrchestrator, TaskConfig
from ..tools.base import ToolRegistry

logger = logging.getLogger(__name__)

# Global orchestrator instance (in production, use dependency injection)
orchestrator: Optional[AgentOrchestrator] = None
tool_registry: Optional[ToolRegistry] = None

# In-memory task storage (in production, use a proper database)
task_storage: Dict[str, TaskResultResponse] = {}

router = APIRouter()


def get_orchestrator() -> AgentOrchestrator:
    """Get orchestrator instance"""
    global orchestrator
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    return orchestrator


def get_tool_registry() -> ToolRegistry:
    """Get tool registry instance"""
    global tool_registry
    if tool_registry is None:
        raise HTTPException(status_code=503, detail="Tool registry not initialized")
    return tool_registry


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        orch = get_orchestrator()
        tools = get_tool_registry()
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow().isoformat(),
            version="1.0.0",
            available_agents=orch.get_available_agents(),
            available_tools=tools.list_tools()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@router.post("/tasks", response_model=TaskStatusResponse)
async def create_task(
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks
) -> TaskStatusResponse:
    """Create and start a new task"""
    try:
        orch = get_orchestrator()
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Convert request config to internal config
        config = None
        if request.config:
            config = TaskConfig(
                timeout=request.config.timeout,
                max_retries=request.config.max_retries,
                retry_delay=request.config.retry_delay,
                retry_backoff=request.config.retry_backoff,
                concurrent_agents=request.config.concurrent_agents
            )
        
        # Create initial task status
        task_status = TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        
        # Store task status
        task_storage[task_id] = TaskResultResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            execution_metadata={"created_at": task_status.created_at}
        )
        
        # Start task execution in background
        background_tasks.add_task(
            execute_task_background,
            task_id,
            request.agent_sequence,
            request.initial_data,
            config
        )
        
        return task_status
        
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


async def execute_task_background(
    task_id: str,
    agent_sequence: List[str],
    initial_data: Optional[Dict],
    config: Optional[TaskConfig]
):
    """Execute task in background"""
    try:
        orch = get_orchestrator()
        
        # Update status to running
        if task_id in task_storage:
            task_storage[task_id].status = TaskStatus.RUNNING
            task_storage[task_id].execution_metadata["started_at"] = datetime.utcnow().isoformat()
        
        # Execute task
        result = await orch.execute_task(
            task_id=task_id,
            agent_sequence=agent_sequence,
            initial_data=initial_data,
            custom_config=config
        )
        
        # Convert result to response format
        agent_results = {}        
        
        # Access agent_results from AddableValuesDict using dict key access
        agent_results_dict = result['agent_results']
        for agent_id, agent_result in agent_results_dict.items():
            agent_results[agent_id] = AgentResultResponse(
                agent_id=agent_result.agent_id,
                status=AgentStatus(agent_result.status.value),
                result=agent_result.result,
                error=agent_result.error,
                execution_time=agent_result.execution_time,
                retry_count=agent_result.retry_count,
                metadata=agent_result.metadata or {}
            )
        
        # Update task storage
        task_storage[task_id] = TaskResultResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED if not result['execution_metadata'].get("error") else TaskStatus.FAILED,
            agent_results=agent_results,
            shared_data=result['shared_data'],
            execution_metadata=result['execution_metadata'],
            total_execution_time=result['execution_metadata'].get("total_execution_time", 0.0)
        )
        
        logger.info(f"Task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        
        # Update task with error
        if task_id in task_storage:
            task_storage[task_id].status = TaskStatus.FAILED
            task_storage[task_id].execution_metadata["error"] = str(e)
            task_storage[task_id].execution_metadata["failed_at"] = datetime.utcnow().isoformat()


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Get task status"""
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = task_storage[task_id]
    
    # Convert agent results
    agent_results = {}
    for agent_id, agent_result in task.agent_results.items():
        agent_results[agent_id] = AgentResultResponse(
            agent_id=agent_result.agent_id,
            status=agent_result.status,
            result=agent_result.result,
            error=agent_result.error,
            execution_time=agent_result.execution_time,
            retry_count=agent_result.retry_count,
            metadata=agent_result.metadata or {}
        )
    
    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        agent_results=agent_results,
        execution_metadata=task.execution_metadata,
        created_at=task.execution_metadata.get("created_at"),
        updated_at=datetime.utcnow().isoformat()
    )


@router.get("/tasks/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(task_id: str) -> TaskResultResponse:
    """Get complete task result"""
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task_storage[task_id]


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a running task"""
    try:
        orch = get_orchestrator()
        
        if task_id not in task_storage:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Cancel task in orchestrator
        cancelled = await orch.cancel_task(task_id)
        
        if cancelled:
            # Update task status
            task_storage[task_id].status = TaskStatus.CANCELLED
            task_storage[task_id].execution_metadata["cancelled_at"] = datetime.utcnow().isoformat()
            
            return {"message": f"Task {task_id} cancelled successfully"}
        else:
            return {"message": f"Task {task_id} was not running or already completed"}
            
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")


@router.get("/tasks", response_model=List[TaskStatusResponse])
async def list_tasks(limit: int = 50, offset: int = 0):
    """List all tasks"""
    tasks = list(task_storage.values())[offset:offset + limit]
    
    result = []
    for task in tasks:
        # Convert agent results
        agent_results = {}
        for agent_id, agent_result in task.agent_results.items():
            agent_results[agent_id] = AgentResultResponse(
                agent_id=agent_result.agent_id,
                status=agent_result.status,
                result=agent_result.result,
                error=agent_result.error,
                execution_time=agent_result.execution_time,
                retry_count=agent_result.retry_count,
                metadata=agent_result.metadata or {}
            )
        
        result.append(TaskStatusResponse(
            task_id=task.task_id,
            status=task.status,
            agent_results=agent_results,
            execution_metadata=task.execution_metadata,
            created_at=task.execution_metadata.get("created_at"),
            updated_at=datetime.utcnow().isoformat()
        ))
    
    return result


@router.post("/tools/{tool_name}/execute", response_model=ToolResultResponse)
async def execute_tool(tool_name: str, request: ToolExecuteRequest):
    """Execute a tool directly"""
    try:
        tools = get_tool_registry()
        
        if tool_name != request.tool_name:
            raise HTTPException(status_code=400, detail="Tool name mismatch")
        
        # Execute tool
        result = await tools.execute_tool(tool_name, **request.parameters)
        
        return ToolResultResponse(
            tool_name=result.tool_name,
            status=result.status.value,
            result=result.result,
            error=result.error,
            execution_time=result.execution_time,
            metadata=result.metadata or {}
        )
        
    except Exception as e:
        logger.error(f"Failed to execute tool {tool_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute tool: {str(e)}")


@router.get("/agents", response_model=List[AgentInfo])
async def list_agents():
    """List all available agents"""
    try:
        orch = get_orchestrator()
        agent_ids = orch.get_available_agents()
        
        agents = []
        for agent_id in agent_ids:
            agents.append(AgentInfo(
                agent_id=agent_id,
                description=f"Agent {agent_id}",
                config=None
            ))
        
        return agents
        
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")


@router.get("/tools", response_model=List[ToolInfo])
async def list_tools():
    """List all available tools"""
    try:
        tools = get_tool_registry()
        tool_names = tools.list_tools()
        
        tool_infos = []
        for tool_name in tool_names:
            tool_infos.append(ToolInfo(
                tool_name=tool_name,
                description=f"Tool {tool_name}",
                parameters=None,
                config=None
            ))
        
        return tool_infos
        
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")


@router.get("/tools/{tool_name}", response_model=ToolInfo)
async def get_tool_info(tool_name: str):
    """Get information about a specific tool"""
    try:
        tools = get_tool_registry()
        tool = tools.get(tool_name)
        
        if not tool:
            raise HTTPException(status_code=404, detail="Tool not found")
        
        return ToolInfo(
            tool_name=tool_name,
            description=f"Tool {tool_name}",
            parameters=None,
            config=tool.config.dict() if hasattr(tool.config, 'dict') else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tool info for {tool_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tool info: {str(e)}")
