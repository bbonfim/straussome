"""
Straussome - Core orchestration engine for managing agent execution,
isolation, result passing, concurrency, retries, and timeouts.
"""

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field
from enum import Enum
import traceback

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from ..agents.base import BaseAgent
from .models import AgentState, AgentResult, AgentStatus, TaskStatus, TaskConfig

logger = logging.getLogger(__name__)






class AgentOrchestrator:
    """Main orchestrator for managing agent execution"""
    
    def __init__(self, config: Optional[TaskConfig] = None, tool_registry=None):
        self.config = config or TaskConfig()
        self.agents: Dict[str, Type[BaseAgent]] = {}
        self.tools: Dict[str, Any] = {}
        self.tool_registry = tool_registry
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_results: Dict[str, AgentState] = {}
        self.checkpointer = MemorySaver()
        self.logger = logging.getLogger("orchestrator")
        
        # Semaphore for controlling concurrent agent execution
        self.semaphore = asyncio.Semaphore(self.config.concurrent_agents)
    
    def register_agent(self, agent_class: Type[BaseAgent], agent_id: str):
        """Register an agent class"""
        self.agents[agent_id] = agent_class
        self.logger.info(f"Registered agent: {agent_id}")
    
    def register_tool(self, tool_name: str, tool_instance: Any):
        """Register a tool for agents to use"""
        self.tools[tool_name] = tool_instance
        self.logger.info(f"Registered tool: {tool_name}")
    
    async def execute_task(
        self,
        task_id: str,
        agent_sequence: List[str],
        initial_data: Optional[Dict[str, Any]] = None,
        custom_config: Optional[TaskConfig] = None
    ) -> AgentState:
        """Execute a sequence of agents as a task"""
        config = custom_config or self.config
        start_time = time.time()
        
        self.logger.info(f"Starting task {task_id} with agents: {agent_sequence}")
        
        # Initialize state
        state = AgentState(
            task_id=task_id,
            shared_data=initial_data or {},
            agent_results={},
            execution_metadata={}
        )
        
        try:
            # Create and execute the agent graph
            graph = self._build_agent_graph(agent_sequence)
            
            # Execute with timeout
            result = await asyncio.wait_for(
                graph.ainvoke(state, config={"configurable": {"thread_id": task_id}}),
                timeout=config.timeout
            )
            
            execution_time = time.time() - start_time
            # Ensure result has execution_metadata
            if not hasattr(result, 'execution_metadata'):
                result.execution_metadata = {}
            result.execution_metadata["total_execution_time"] = execution_time
            
            self.logger.info(f"Task {task_id} completed in {execution_time:.2f}s")
            return result
            
        except asyncio.TimeoutError:
            self.logger.error(f"Task {task_id} timed out after {config.timeout}s")
            state.execution_metadata["error"] = "Task timeout"
            state.execution_metadata["status"] = TaskStatus.FAILED
            return state
            
        except Exception as e:
            self.logger.error(f"Task {task_id} failed: {str(e)}")
            self.logger.error(traceback.format_exc())
            state.execution_metadata["error"] = str(e)
            state.execution_metadata["status"] = TaskStatus.FAILED
            return state
    
    def _build_agent_graph(self, agent_sequence: List[str]) -> StateGraph:
        """Build a LangGraph from agent sequence"""
        graph = StateGraph(AgentState)
        
        # Add nodes for each agent
        for agent_id in agent_sequence:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not registered")
            
            graph.add_node(agent_id, self._create_agent_node(agent_id))
        
        # Add entry point from START to first agent
        if agent_sequence:
            graph.add_edge("__start__", agent_sequence[0])
        
        # Connect agents in sequence
        for i in range(len(agent_sequence) - 1):
            graph.add_edge(agent_sequence[i], agent_sequence[i + 1])
        
        # Add end edge
        if agent_sequence:
            graph.add_edge(agent_sequence[-1], "__end__")
        
        return graph.compile(checkpointer=self.checkpointer)
    
    def _create_agent_node(self, agent_id: str):
        """Create a node function for an agent"""
        async def agent_node(state: AgentState) -> AgentState:
            agent_class = self.agents[agent_id]
            agent = agent_class(agent_id, self.config.__dict__, self.tool_registry)
            
            # Create agent result
            agent_result = AgentResult(
                agent_id=agent_id,
                task_id=state.task_id,
                status=AgentStatus.RUNNING
            )
            
            start_time = time.time()
            
            try:
                # Execute agent with retry logic
                result_state = await self._execute_agent_with_retry(agent, state, agent_result)
                
                execution_time = time.time() - start_time
                agent_result.execution_time = execution_time
                agent_result.status = AgentStatus.COMPLETED
                agent_result.result = result_state.shared_data.get(f"{agent_id}_result")
                
                # Store result in state
                if not hasattr(result_state, 'agent_results'):
                    result_state.agent_results = {}
                result_state.agent_results[agent_id] = agent_result
                
                return result_state
                
            except Exception as e:
                execution_time = time.time() - start_time
                agent_result.execution_time = execution_time
                agent_result.status = AgentStatus.FAILED
                agent_result.error = str(e)
                
                if not hasattr(state, 'agent_results'):
                    state.agent_results = {}
                if not hasattr(state, 'execution_metadata'):
                    state.execution_metadata = {}
                state.agent_results[agent_id] = agent_result
                state.execution_metadata["error"] = str(e)
                
                self.logger.error(f"Agent {agent_id} failed: {str(e)}")
                raise
            
            finally:
                await agent.cleanup()
        
        return agent_node
    
    async def _execute_agent_with_retry(
        self,
        agent: BaseAgent,
        state: AgentState,
        agent_result: AgentResult
    ) -> AgentState:
        """Execute agent with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                if attempt > 0:
                    agent_result.status = AgentStatus.RETRYING
                    agent_result.retry_count = attempt
                    
                    delay = self.config.retry_delay * (self.config.retry_backoff ** (attempt - 1))
                    self.logger.info(f"Retrying agent {agent.agent_id} in {delay}s (attempt {attempt})")
                    await asyncio.sleep(delay)
                
                # Execute with semaphore for concurrency control
                async with self.semaphore:
                    return await agent.execute(state)
                    
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Agent {agent.agent_id} attempt {attempt + 1} failed: {str(e)}")
                
                if attempt == self.config.max_retries:
                    break
        
        # All retries failed
        raise last_exception
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a running or completed task"""
        if task_id in self.task_results:
            state = self.task_results[task_id]
            return {
                "task_id": task_id,
                "status": state.execution_metadata.get("status", TaskStatus.RUNNING),
                "agent_results": {
                    agent_id: {
                        "status": result.status,
                        "execution_time": result.execution_time,
                        "retry_count": result.retry_count,
                        "error": result.error
                    }
                    for agent_id, result in state.agent_results.items()
                },
                "execution_metadata": state.execution_metadata
            }
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.cancel()
            del self.running_tasks[task_id]
            self.logger.info(f"Cancelled task {task_id}")
            return True
        return False
    
    def get_available_agents(self) -> List[str]:
        """Get list of available agent IDs"""
        return list(self.agents.keys())
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return list(self.tools.keys())
