"""
LLM integration tools for AI-powered processing
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union
import openai
from openai import AsyncOpenAI

from .base import BaseTool, ToolResult, ToolStatus, ToolConfig


class LLMTool(BaseTool):
    """Tool for interacting with Large Language Models"""
    
    def __init__(self, name: str = "llm", config: Optional[ToolConfig] = None):
        super().__init__(name, config)
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenAI client"""
        try:
            # In a real implementation, you'd get the API key from environment
            api_key = "your-openai-api-key"  # This should come from env vars
            self.client = AsyncOpenAI(api_key=api_key)
        except Exception as e:
            self.logger.warning(f"Failed to initialize OpenAI client: {e}")
            self.client = None
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute LLM operation"""
        start_time = time.time()
        
        try:
            operation = kwargs.get("operation", "chat")
            prompt = kwargs.get("prompt", "")
            model = kwargs.get("model", "gpt-3.5-turbo")
            max_tokens = kwargs.get("max_tokens", 1000)
            temperature = kwargs.get("temperature", 0.7)
            
            if not prompt:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error="Prompt is required"
                )
            
            self.logger.info(f"Executing LLM operation: {operation}")
            
            if operation == "chat":
                result = await self._chat_completion(prompt, model, max_tokens, temperature)
            elif operation == "completion":
                result = await self._text_completion(prompt, model, max_tokens, temperature)
            elif operation == "embedding":
                result = await self._create_embedding(prompt, model)
            elif operation == "analysis":
                result = await self._analyze_data(prompt, kwargs.get("data"))
            else:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error=f"Unsupported operation: {operation}"
                )
            
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"LLM error: {str(e)}",
                execution_time=execution_time
            )
    
    async def _chat_completion(self, prompt: str, model: str, max_tokens: int, temperature: float) -> ToolResult:
        """Generate chat completion"""
        try:
            if not self.client:
                # Mock response for demo
                response_text = f"Mock LLM response to: {prompt[:50]}..."
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.COMPLETED,
                    result={"response": response_text, "model": model},
                    metadata={"operation": "chat", "tokens_used": len(prompt.split())}
                )
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            response_text = response.choices[0].message.content
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                result={"response": response_text, "model": model},
                metadata={
                    "operation": "chat",
                    "tokens_used": response.usage.total_tokens if response.usage else 0
                }
            )
            
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Chat completion error: {str(e)}"
            )
    
    async def _text_completion(self, prompt: str, model: str, max_tokens: int, temperature: float) -> ToolResult:
        """Generate text completion"""
        try:
            if not self.client:
                # Mock response for demo
                response_text = f"Mock completion for: {prompt[:50]}..."
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.COMPLETED,
                    result={"completion": response_text, "model": model},
                    metadata={"operation": "completion"}
                )
            
            response = await self.client.completions.create(
                model=model,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            completion_text = response.choices[0].text
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                result={"completion": completion_text, "model": model},
                metadata={"operation": "completion"}
            )
            
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Text completion error: {str(e)}"
            )
    
    async def _create_embedding(self, text: str, model: str) -> ToolResult:
        """Create text embedding"""
        try:
            if not self.client:
                # Mock embedding for demo
                mock_embedding = [0.1] * 1536  # Typical embedding size
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.COMPLETED,
                    result={"embedding": mock_embedding, "model": model},
                    metadata={"operation": "embedding", "dimensions": len(mock_embedding)}
                )
            
            response = await self.client.embeddings.create(
                model=model,
                input=text
            )
            
            embedding = response.data[0].embedding
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                result={"embedding": embedding, "model": model},
                metadata={"operation": "embedding", "dimensions": len(embedding)}
            )
            
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Embedding error: {str(e)}"
            )
    
    async def _analyze_data(self, analysis_prompt: str, data: Any) -> ToolResult:
        """Analyze data using LLM"""
        try:
            # Combine prompt with data
            if isinstance(data, (list, dict)):
                data_str = json.dumps(data, indent=2)
            else:
                data_str = str(data)
            
            full_prompt = f"{analysis_prompt}\n\nData to analyze:\n{data_str}"
            
            # Use chat completion for analysis
            result = await self._chat_completion(full_prompt, "gpt-3.5-turbo", 2000, 0.3)
            
            if result.status == ToolStatus.COMPLETED:
                result.metadata["operation"] = "analysis"
                result.metadata["data_size"] = len(data_str)
            
            return result
            
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Data analysis error: {str(e)}"
            )
    
    async def cleanup(self):
        """Cleanup LLM client"""
        if self.client:
            # OpenAI client doesn't need explicit cleanup
            pass
