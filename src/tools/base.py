"""
Base classes for pluggable tools system
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field


class ToolStatus(str, Enum):
    """Tool execution status"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ToolResult:
    """Result from tool execution"""
    tool_name: str
    status: ToolStatus
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ToolConfig(BaseModel):
    """Configuration for tool execution"""
    timeout: float = 30.0
    max_retries: int = 2
    retry_delay: float = 1.0
    cache_enabled: bool = True
    cache_ttl: int = 300  # 5 minutes


class BaseTool(ABC):
    """Base class for all tools"""
    
    def __init__(self, name: str, config: Optional[ToolConfig] = None):
        self.name = name
        self.config = config or ToolConfig()
        self.logger = logging.getLogger(f"tool.{name}")
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters"""
        pass
    
    async def execute_with_retry(self, **kwargs) -> ToolResult:
        """Execute tool with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                if attempt > 0:
                    delay = self.config.retry_delay * (2 ** (attempt - 1))
                    self.logger.info(f"Retrying {self.name} in {delay}s (attempt {attempt})")
                    await asyncio.sleep(delay)
                
                return await asyncio.wait_for(
                    self.execute(**kwargs),
                    timeout=self.config.timeout
                )
                
            except asyncio.TimeoutError:
                last_exception = Exception(f"Tool {self.name} timed out after {self.config.timeout}s")
                self.logger.warning(f"Tool {self.name} timed out on attempt {attempt + 1}")
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Tool {self.name} attempt {attempt + 1} failed: {str(e)}")
                
                if attempt == self.config.max_retries:
                    break
        
        # All retries failed
        return ToolResult(
            tool_name=self.name,
            status=ToolStatus.FAILED,
            error=str(last_exception)
        )
    
    def _get_cache_key(self, **kwargs) -> str:
        """Generate cache key from parameters"""
        import hashlib
        import json
        
        # Sort kwargs for consistent hashing
        sorted_kwargs = {k: v for k, v in sorted(kwargs.items())}
        key_str = f"{self.name}:{json.dumps(sorted_kwargs, sort_keys=True)}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached result is still valid"""
        if not self.config.cache_enabled:
            return False
        
        if cache_key not in self._cache_timestamps:
            return False
        
        import time
        return (time.time() - self._cache_timestamps[cache_key]) < self.config.cache_ttl
    
    def _get_cached_result(self, cache_key: str) -> Optional[ToolResult]:
        """Get cached result if valid"""
        if self._is_cache_valid(cache_key):
            self.logger.debug(f"Using cached result for {self.name}")
            return self._cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: ToolResult):
        """Cache the result"""
        if self.config.cache_enabled:
            import time
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = time.time()
    
    async def __call__(self, **kwargs) -> ToolResult:
        """Make tool callable"""
        # Check cache first
        cache_key = self._get_cache_key(**kwargs)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Execute with retry
        result = await self.execute_with_retry(**kwargs)
        
        # Cache successful results
        if result.status == ToolStatus.COMPLETED:
            self._cache_result(cache_key, result)
        
        return result
    
    async def cleanup(self):
        """Cleanup tool resources"""
        pass


class ToolRegistry:
    """Registry for managing tools"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.logger = logging.getLogger("tool_registry")
    
    def register(self, tool: BaseTool):
        """Register a tool"""
        self.tools[tool.name] = tool
        self.logger.info(f"Registered tool: {tool.name}")
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self.tools.keys())
    
    async def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name"""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                tool_name=name,
                status=ToolStatus.FAILED,
                error=f"Tool {name} not found"
            )
        
        return await tool(**kwargs)
    
    async def cleanup_all(self):
        """Cleanup all tools"""
        for tool in self.tools.values():
            await tool.cleanup()
