"""
Data fetching tools for retrieving data from various sources
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union
import httpx
import pandas as pd

from .base import BaseTool, ToolResult, ToolStatus, ToolConfig


class DataFetcherTool(BaseTool):
    """Tool for fetching data from HTTP APIs"""
    
    def __init__(self, name: str = "data_fetcher", config: Optional[ToolConfig] = None):
        super().__init__(name, config)
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Fetch data from HTTP endpoint"""
        start_time = time.time()
        
        try:
            url = kwargs.get("url")
            method = kwargs.get("method", "GET").upper()
            headers = kwargs.get("headers", {})
            params = kwargs.get("params", {})
            data = kwargs.get("data")
            json_data = kwargs.get("json")
            
            if not url:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error="URL is required"
                )
            
            self.logger.info(f"Fetching data from {url}")
            
            # Make HTTP request
            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json_data
            )
            
            response.raise_for_status()
            
            # Parse response
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                result_data = response.json()
            elif "text/csv" in content_type:
                result_data = pd.read_csv(response.text).to_dict("records")
            else:
                result_data = response.text
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                result=result_data,
                execution_time=execution_time,
                metadata={
                    "url": url,
                    "method": method,
                    "status_code": response.status_code,
                    "content_type": content_type,
                    "response_size": len(response.content)
                }
            )
            
        except httpx.HTTPError as e:
            execution_time = time.time() - start_time
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"HTTP error: {str(e)}",
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Unexpected error: {str(e)}",
                execution_time=execution_time
            )
    
    async def cleanup(self):
        """Cleanup HTTP client"""
        await self.client.aclose()


class DatabaseFetcherTool(BaseTool):
    """Tool for fetching data from databases"""
    
    def __init__(self, name: str = "database_fetcher", config: Optional[ToolConfig] = None):
        super().__init__(name, config)
        self.connections: Dict[str, Any] = {}
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute database query"""
        start_time = time.time()
        
        try:
            connection_string = kwargs.get("connection_string")
            query = kwargs.get("query")
            params = kwargs.get("params", {})
            
            if not connection_string or not query:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error="connection_string and query are required"
                )
            
            # For demo purposes, we'll simulate database access
            # In a real implementation, you'd use SQLAlchemy or similar
            self.logger.info(f"Executing database query: {query[:100]}...")
            
            # Simulate database query execution
            await asyncio.sleep(0.1)  # Simulate network delay
            
            # Mock result
            result_data = [
                {"id": 1, "name": "Sample Data 1", "value": 100},
                {"id": 2, "name": "Sample Data 2", "value": 200},
                {"id": 3, "name": "Sample Data 3", "value": 300}
            ]
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                result=result_data,
                execution_time=execution_time,
                metadata={
                    "query": query,
                    "row_count": len(result_data)
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Database error: {str(e)}",
                execution_time=execution_time
            )
    
    async def cleanup(self):
        """Cleanup database connections"""
        for conn in self.connections.values():
            if hasattr(conn, 'close'):
                await conn.close()


class FileFetcherTool(BaseTool):
    """Tool for reading data from files"""
    
    def __init__(self, name: str = "file_fetcher", config: Optional[ToolConfig] = None):
        super().__init__(name, config)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Read data from file"""
        start_time = time.time()
        
        try:
            file_path = kwargs.get("file_path")
            file_type = kwargs.get("file_type", "auto")
            
            if not file_path:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error="file_path is required"
                )
            
            self.logger.info(f"Reading file: {file_path}")
            
            # Determine file type
            if file_type == "auto":
                if file_path.endswith(('.json', '.JSON')):
                    file_type = "json"
                elif file_path.endswith(('.csv', '.CSV')):
                    file_type = "csv"
                elif file_path.endswith(('.txt', '.TXT')):
                    file_type = "text"
                else:
                    file_type = "text"
            
            # Read file based on type
            if file_type == "json":
                with open(file_path, 'r') as f:
                    result_data = json.load(f)
            elif file_type == "csv":
                result_data = pd.read_csv(file_path).to_dict("records")
            else:  # text
                with open(file_path, 'r') as f:
                    result_data = f.read()
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                result=result_data,
                execution_time=execution_time,
                metadata={
                    "file_path": file_path,
                    "file_type": file_type,
                    "file_size": len(str(result_data))
                }
            )
            
        except FileNotFoundError:
            execution_time = time.time() - start_time
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"File not found: {file_path}",
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"File reading error: {str(e)}",
                execution_time=execution_time
            )
