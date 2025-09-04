"""
Configuration management for the agent orchestrator
"""

import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class APISettings(BaseSettings):
    """API configuration settings"""
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    debug: bool = Field(default=False, env="API_DEBUG")
    title: str = "Straussome"
    version: str = "1.0.0"
    description: str = "A powerful agent orchestration system with pluggable tools"
    
    class Config:
        env_file = ".env"


class OrchestratorSettings(BaseSettings):
    """Orchestrator configuration settings"""
    timeout: float = Field(default=300.0, env="ORCHESTRATOR_TIMEOUT")
    max_retries: int = Field(default=3, env="ORCHESTRATOR_MAX_RETRIES")
    retry_delay: float = Field(default=1.0, env="ORCHESTRATOR_RETRY_DELAY")
    retry_backoff: float = Field(default=2.0, env="ORCHESTRATOR_RETRY_BACKOFF")
    concurrent_agents: int = Field(default=5, env="ORCHESTRATOR_CONCURRENT_AGENTS")
    
    class Config:
        env_file = ".env"


class DatabaseSettings(BaseSettings):
    """Database configuration settings"""
    url: str = Field(default="sqlite:///./orchestrator.db", env="DATABASE_URL")
    echo: bool = Field(default=False, env="DATABASE_ECHO")
    pool_size: int = Field(default=5, env="DATABASE_POOL_SIZE")
    max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    
    class Config:
        env_file = ".env"


class OpenAISettings(BaseSettings):
    """OpenAI configuration settings"""
    api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    model: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")
    max_tokens: int = Field(default=1000, env="OPENAI_MAX_TOKENS")
    temperature: float = Field(default=0.7, env="OPENAI_TEMPERATURE")
    
    class Config:
        env_file = ".env"


class LoggingSettings(BaseSettings):
    """Logging configuration settings"""
    level: str = Field(default="INFO", env="LOG_LEVEL")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    file_path: Optional[str] = Field(default=None, env="LOG_FILE_PATH")
    max_file_size: int = Field(default=10485760, env="LOG_MAX_FILE_SIZE")  # 10MB
    backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    
    class Config:
        env_file = ".env"


class ToolSettings(BaseSettings):
    """Tool configuration settings"""
    cache_enabled: bool = Field(default=True, env="TOOL_CACHE_ENABLED")
    cache_ttl: int = Field(default=300, env="TOOL_CACHE_TTL")
    timeout: float = Field(default=30.0, env="TOOL_TIMEOUT")
    max_retries: int = Field(default=2, env="TOOL_MAX_RETRIES")
    retry_delay: float = Field(default=1.0, env="TOOL_RETRY_DELAY")
    
    class Config:
        env_file = ".env"


class SecuritySettings(BaseSettings):
    """Security configuration settings"""
    secret_key: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="ALLOWED_ORIGINS"
    )
    enable_cors: bool = Field(default=True, env="ENABLE_CORS")
    
    class Config:
        env_file = ".env"
    
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse comma-separated origins"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


class MonitoringSettings(BaseSettings):
    """Monitoring configuration settings"""
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    class Config:
        env_file = ".env"


class Settings:
    """Main settings class that combines all configuration"""
    
    def __init__(self):
        self.api = APISettings()
        self.orchestrator = OrchestratorSettings()
        self.database = DatabaseSettings()
        self.openai = OpenAISettings()
        self.logging = LoggingSettings()
        self.tool = ToolSettings()
        self.security = SecuritySettings()
        self.monitoring = MonitoringSettings()
    
    def validate(self) -> bool:
        """Validate all settings"""
        try:
            # Validate required settings
            if not self.security.secret_key or self.security.secret_key == "your-secret-key-here":
                print("Warning: Using default secret key. Please set SECRET_KEY in environment.")
            
            if not self.openai.api_key:
                print("Warning: OpenAI API key not set. LLM features will use mock responses.")
            
            return True
        except Exception as e:
            print(f"Settings validation failed: {e}")
            return False
    
    def to_dict(self) -> dict:
        """Convert settings to dictionary"""
        return {
            "api": self.api.dict(),
            "orchestrator": self.orchestrator.dict(),
            "database": self.database.dict(),
            "openai": self.openai.dict(),
            "logging": self.logging.dict(),
            "tool": self.tool.dict(),
            "security": self.security.dict(),
            "monitoring": self.monitoring.dict()
        }


# Global settings instance
settings = Settings()
