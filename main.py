"""
Main entry point for Straussome
"""

import logging
import sys
import warnings
from pathlib import Path

# Suppress urllib3 OpenSSL warnings
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL 1.1.1+")

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.api.app import app
from src.config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.logging.level.upper()),
    format=settings.logging.format,
    handlers=[      
        logging.StreamHandler(sys.stdout),
    ]   
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    import uvicorn
    
    # Validate settings
    if not settings.validate():
        logger.error("Settings validation failed")
        sys.exit(1)
    
    logger.info("Starting Straussome...")
    logger.info(f"API will be available at http://{settings.api.host}:{settings.api.port}")
    logger.info(f"API documentation at http://{settings.api.host}:{settings.api.port}/docs")
    
    uvicorn.run(
        app,
        host=settings.api.host,
        port=settings.api.port,
        log_level=settings.logging.level.lower(),
        reload=settings.api.debug
    )
