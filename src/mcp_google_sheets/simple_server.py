#!/usr/bin/env python
"""
Simple HTTP server for Railway testing
"""

import logging
from fastapi import FastAPI
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Simple Test Server",
    description="Minimal server for Railway testing",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Health check endpoint"""
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "message": "Simple server is running",
        "version": "1.0.0"
    }

@app.get("/test")
async def test():
    """Test endpoint"""
    logger.info("Test endpoint requested")
    return {"message": "Test successful"}

def main():
    """Main function to start the server"""
    logger.info("Starting Simple Test Server")
    logger.info("Server will be available at http://0.0.0.0:8000")
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        raise

if __name__ == "__main__":
    main()
