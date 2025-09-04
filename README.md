# Straussome

A simple agent orchestration system built with FastAPI and LangGraph. This system enables you to run agents in isolation while allowing them to pass results to each other, with built-in support for concurrency, retries, timeouts, and pluggable tools.

## 🚀 Features

- **Agent Isolation**: Agents run in complete isolation but can pass results to subsequent agents
- **Concurrency Control**: Built-in concurrency limits and semaphore-based execution control
- **Retry & Timeout Handling**: Configurable retry logic with exponential backoff and timeout management
- **Pluggable Tools**: Extensible tool system for data fetching, chart generation, LLM integration, and more
- **Clear API**: RESTful API designed for frontend consumption with comprehensive documentation
- **Error Handling**: Robust error handling with structured logging and custom exception types
- **Configuration Management**: Environment-based configuration with validation
- **Real-time Monitoring**: Task status tracking and execution monitoring

## Trade-offs
Because of time constraints, here are some trade-offs made:

 - **In-memory data sharing between agents**: With the current implementation, the shared data between agents is lost if the server crashes. In a production grade version, we could use Redis to have better failure coverage and also allow for better scaling across multiple server instances.
 - **Static agent registry**: You will need to reboot the app for a new agent to be available. Ideally this would be externalized on proper infrastructure and agents can be seen as "small services" running on pods or the like (zero downtime). Kubernetes would work well for this scenario and even help with service discovery and load balancing out of the box.
 - **Agents within tasks run in sequence**: While multiple tasks can run in parallel, agents within a single task execute sequentially. For the sake of time and complexity, we avoided implementing complex dependency graphs. In production, you could use Redis or a workflow engine to manage agent dependencies and enable parallel execution where possible.
 - **Limited error recovery**: While we have retry logic, there's no sophisticated error recovery or circuit breaker patterns for handling cascading failures.
 - **No authentication/authorization**: The API is currently open without any security measures. Production deployments would need proper authentication, API keys, or OAuth integration.

## 📋 Requirements

- Python 3.8+
- FastAPI
- LangGraph
- See `requirements.txt` for complete dependencies

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd strauss
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

## 🏗️ Architecture

### Core Components

1. **Orchestrator** (`src/core/orchestrator.py`): Main orchestration engine
2. **Tools** (`src/tools/`): Pluggable tool system
3. **Agents** (`src/agents/`): Example agent implementations
4. **API** (`src/api/`): FastAPI endpoints and models
5. **Configuration** (`src/config/`): Environment-based configuration

### Agent Execution Flow

```
Task Creation → Agent Sequence → Execution with Retries → Result Collection → Task Completion
```

## 📖 Usage Examples

### API Endpoints with CURL Examples

#### Health Check
```bash
curl -X GET "http://localhost:8000/api/v1/health" \
  -H "Content-Type: application/json"
```

#### Create a Task
```bash
curl -X POST "http://localhost:8000/api/v1/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_sequence": ["data_analyzer", "chart_generator"],
    "initial_data": {
      "dataset_name": "sales_data_2024",
      "analysis_type": "comprehensive"
    },
    "config": {
      "timeout": 300.0,
      "max_retries": 3,
      "retry_delay": 1.0,
      "retry_backoff": 2.0,
      "concurrent_agents": 5
    }
  }'
```

#### Get Task Status
```bash
curl -X GET "http://localhost:8000/api/v1/tasks/{task_id}" \
  -H "Content-Type: application/json"
```

#### Get Task Results
```bash
curl -X GET "http://localhost:8000/api/v1/tasks/{task_id}/result" \
  -H "Content-Type: application/json"
```

#### List All Tasks
```bash
curl -X GET "http://localhost:8000/api/v1/tasks?limit=10&offset=0" \
  -H "Content-Type: application/json"
```

#### Cancel a Task
```bash
curl -X DELETE "http://localhost:8000/api/v1/tasks/{task_id}" \
  -H "Content-Type: application/json"
```

#### List Available Agents
```bash
curl -X GET "http://localhost:8000/api/v1/agents" \
  -H "Content-Type: application/json"
```

#### List Available Tools
```bash
curl -X GET "http://localhost:8000/api/v1/tools" \
  -H "Content-Type: application/json"
```

#### Get Tool Information
```bash
curl -X GET "http://localhost:8000/api/v1/tools/{tool_name}" \
  -H "Content-Type: application/json"
```

#### Execute Tool Directly
```bash
curl -X POST "http://localhost:8000/api/v1/tools/data_fetcher/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "data_fetcher",
    "parameters": {
      "url": "https://jsonplaceholder.typicode.com/posts",
      "method": "GET"
    }
  }'
```

### Complete Workflow Example

1. **Create a task** with data analysis and chart generation:
```bash
TASK_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_sequence": ["data_analyzer", "chart_generator"],
    "initial_data": {
      "dataset_name": "user_activity",
      "analysis_type": "comprehensive"
    }
  }')

TASK_ID=$(echo $TASK_RESPONSE | jq -r '.task_id')
echo "Created task: $TASK_ID"
```

2. **Monitor task progress**:
```bash
# Check status
curl -s -X GET "http://localhost:8000/api/v1/tasks/$TASK_ID" | jq '.'

# Wait for completion and get results
curl -s -X GET "http://localhost:8000/api/v1/tasks/$TASK_ID/result" | jq '.'
```


## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# Orchestrator Configuration
ORCHESTRATOR_TIMEOUT=300
ORCHESTRATOR_MAX_RETRIES=3
ORCHESTRATOR_CONCURRENT_AGENTS=5

# OpenAI Configuration (optional)
OPENAI_API_KEY=your-api-key-here

# Logging
LOG_LEVEL=INFO
```

### Task Configuration

You can customize task execution:

```python
task_config = {
    "timeout": 600,  # 10 minutes
    "max_retries": 5,
    "retry_delay": 2.0,
    "concurrent_agents": 3
}

task_data = {
    "agent_sequence": ["agent1", "agent2"],
    "config": task_config
}
```

## 🛠️ Creating Custom Agents

### Basic Agent Structure

```python
from src.core.orchestrator import BaseAgent, AgentState

class MyCustomAgent(BaseAgent):
    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config)
    
    async def execute(self, state: AgentState) -> AgentState:
        """Implement your agent logic here"""
        
        # Access shared data from previous agents
        previous_data = state.shared_data.get("previous_agent_result")
        
        # Your processing logic
        result = await self.process_data(previous_data)
        
        # Store result for next agents
        state.shared_data[f"{self.agent_id}_result"] = result
        
        return state
    
    async def process_data(self, data):
        # Your custom processing logic
        return {"processed": data}
```

### Registering Your Agent

```python
from src.core.orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator()
orchestrator.register_agent(MyCustomAgent, "my_custom_agent")
```

## 🔌 Creating Custom Tools

### Basic Tool Structure

```python
from src.tools.base import BaseTool, ToolResult, ToolStatus

class MyCustomTool(BaseTool):
    def __init__(self, name: str = "my_tool", config: Optional[ToolConfig] = None):
        super().__init__(name, config)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Implement your tool logic here"""
        
        try:
            # Your tool logic
            input_data = kwargs.get("input_data")
            result = await self.process(input_data)
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                result=result
            )
            
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e)
            )
    
    async def process(self, data):
        # Your custom processing logic
        return {"processed": data}
```

### Registering Your Tool

```python
from src.tools.base import ToolRegistry

tool_registry = ToolRegistry()
tool_registry.register(MyCustomTool())
```

## 📊 Available Tools

### Data Fetcher Tool
- **Purpose**: Fetch data from HTTP APIs, databases, or files
- **Parameters**: `url`, `method`, `headers`, `params`, `data`
- **Example**: Fetch JSON data from REST API

### Chart Generator Tool
- **Purpose**: Generate various types of charts and visualizations
- **Parameters**: `data`, `chart_type`, `title`, `x_column`, `y_column`
- **Supported Types**: line, bar, scatter, pie, heatmap

### LLM Tool
- **Purpose**: Integrate with Large Language Models
- **Parameters**: `operation`, `prompt`, `model`, `max_tokens`
- **Operations**: chat, completion, embedding, analysis

## 🔍 API Endpoints

### Task Management
- `POST /api/v1/tasks` - Create a new task
- `GET /api/v1/tasks/{task_id}` - Get task status
- `GET /api/v1/tasks/{task_id}/result` - Get task result
- `DELETE /api/v1/tasks/{task_id}` - Cancel a task
- `GET /api/v1/tasks` - List all tasks

### Tool Management
- `POST /api/v1/tools/{tool_name}/execute` - Execute a tool
- `GET /api/v1/tools` - List available tools
- `GET /api/v1/tools/{tool_name}` - Get tool information

### System
- `GET /api/v1/health` - Health check
- `GET /api/v1/agents` - List available agents

