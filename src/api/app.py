"""
FastAPI application setup
"""

import logging
import warnings
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Suppress urllib3 OpenSSL warnings
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL 1.1.1+")

from .routes import router
from ..core.orchestrator import AgentOrchestrator, TaskConfig
from ..tools.base import ToolRegistry
from ..tools.data_fetcher import DataFetcherTool, DatabaseFetcherTool, FileFetcherTool
from ..tools.chart_generator import ChartGeneratorTool
from ..tools.llm_tool import LLMTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
orchestrator: AgentOrchestrator = None
tool_registry: ToolRegistry = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global orchestrator, tool_registry
    
    # Startup
    logger.info("Starting Straussome...")
    
    try:
        # Initialize tool registry
        tool_registry = ToolRegistry()
        
        # Register default tools
        await register_default_tools()
        
        # Initialize orchestrator with tool registry
        orchestrator = AgentOrchestrator(TaskConfig(), tool_registry)
        
        # Register default agents
        await register_default_agents()
        
        # Set global instances in routes module
        from . import routes
        routes.orchestrator = orchestrator
        routes.tool_registry = tool_registry
        
        logger.info("Straussome started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start API: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Straussome...")
    
    try:
        if tool_registry:
            await tool_registry.cleanup_all()
        logger.info("Cleanup completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


async def register_default_tools():
    """Register default tools"""
    global tool_registry
    
    # Data fetching tools
    tool_registry.register(DataFetcherTool())
    tool_registry.register(DatabaseFetcherTool())
    tool_registry.register(FileFetcherTool())
    
    # Chart generation tool
    tool_registry.register(ChartGeneratorTool())
    
    # LLM tool
    tool_registry.register(LLMTool())
    
    logger.info(f"Registered {len(tool_registry.list_tools())} default tools")


async def register_default_agents():
    """Register default agents"""
    global orchestrator
    
    # Import and register example agents
    from ..agents.data_analyzer import DataAnalysisAgent
    from ..agents.chart_generator import ChartGenerationAgent
    from ..agents.report_generator import ReportGenerationAgent
    
    orchestrator.register_agent(DataAnalysisAgent, "data_analyzer")
    orchestrator.register_agent(ChartGenerationAgent, "chart_generator")
    orchestrator.register_agent(ReportGenerationAgent, "report_generator")
    
    logger.info(f"Registered {len(orchestrator.get_available_agents())} default agents")


# Create FastAPI app
app = FastAPI(
    title="Straussome",
    description="A powerful agent orchestration system with pluggable tools",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1", tags=["orchestrator"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Straussome",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if app.debug else "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
