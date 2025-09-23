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
    import os
    
    # Get port from Railway environment variable, default to 8000
    port = int(os.environ.get("PORT", 8000))
    
    logger.info(f"Starting Simple Test Server")
    logger.info(f"Server will be available at http://0.0.0.0:{port}")
    logger.info(f"Railway PORT environment variable: {os.environ.get('PORT', 'Not set')}")
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        raise

if __name__ == "__main__":
    main()
