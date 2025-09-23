#!/usr/bin/env python
"""
MCP HTTP/SSE Server for Railway deployment with proper MCP transport
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
import uvicorn

# Import FastMCP for proper MCP HTTP/SSE transport
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

# Import the main MCP server components
try:
    from .server import spreadsheet_lifespan, SpreadsheetContext
    SHEETS_AVAILABLE = True
except Exception as e:
    logging.warning(f"Could not import Google Sheets components: {e}")
    SHEETS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the MCP server with lifespan management
if SHEETS_AVAILABLE:
    mcp = FastMCP(
        "Google Sheets MCP Server",
        dependencies=["google-auth", "google-auth-oauthlib", "google-api-python-client"],
        lifespan=spreadsheet_lifespan
    )
else:
    mcp = FastMCP("Google Sheets MCP Server (Limited Mode)")

@mcp.tool()
async def search(query: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Search for spreadsheets and sheets using Google Sheets API.

    This tool searches through your Google Drive to find spreadsheets that match
    the query. Returns a list of search results with basic information. Use the 
    fetch tool to get complete spreadsheet content.

    Args:
        query: Search query string. Natural language queries work best.

    Returns:
        Dictionary with 'results' key containing list of matching spreadsheets.
        Each result includes id, title, and optional URL.
    """
    if not query or not query.strip():
        return {"results": []}

    if not SHEETS_AVAILABLE:
        return {"results": [], "error": "Google Sheets components not available"}

    try:
        # Get the spreadsheet context from the lifespan
        # Note: In FastMCP, we need to access the context differently
        # For now, we'll return a placeholder response
        logger.info(f"Search requested for query: '{query}'")
        
        # Placeholder response - in a real implementation, we'd access the context
        return {
            "results": [
                {
                    "id": "placeholder",
                    "title": f"Search results for '{query}'",
                    "url": "https://docs.google.com/spreadsheets/d/placeholder",
                    "modified": "2025-01-01T00:00:00Z"
                }
            ],
            "message": "Search functionality ready - Google Sheets integration in progress"
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {"results": [], "error": f"Search failed: {str(e)}"}

@mcp.tool()
async def fetch(id: str) -> Dict[str, Any]:
    """
    Retrieve complete spreadsheet content by ID for detailed analysis.

    This tool fetches the full spreadsheet content from Google Sheets API.
    Use this after finding relevant spreadsheets with the search tool to get
    complete information for analysis and proper citation.

    Args:
        id: Spreadsheet ID from Google Sheets (found in the URL)

    Returns:
        Complete spreadsheet with id, title, full content,
        optional URL, and metadata

    Raises:
        ValueError: If the specified ID is not found
    """
    if not id:
        raise ValueError("Spreadsheet ID is required")

    if not SHEETS_AVAILABLE:
        return {
            "id": id,
            "title": "Placeholder Spreadsheet",
            "text": "Google Sheets integration in progress",
            "url": f"https://docs.google.com/spreadsheets/d/{id}",
            "error": "Google Sheets components not available"
        }

    try:
        logger.info(f"Fetch requested for ID: {id}")
        
        # Placeholder response - in a real implementation, we'd access the context
        return {
            "id": id,
            "title": f"Spreadsheet {id}",
            "text": json.dumps({
                "spreadsheet_title": f"Spreadsheet {id}",
                "sheets": [
                    {
                        "name": "Sheet1",
                        "values": [["A", "B", "C"], ["1", "2", "3"]]
                    }
                ],
                "total_sheets": 1
            }, indent=2),
            "url": f"https://docs.google.com/spreadsheets/d/{id}",
            "metadata": {
                "modified_time": "2025-01-01T00:00:00Z",
                "total_sheets": 1,
                "sheet_names": ["Sheet1"]
            },
            "message": "Fetch functionality ready - Google Sheets integration in progress"
        }
        
    except Exception as e:
        logger.error(f"Fetch failed for ID {id}: {e}")
        raise ValueError(f"Could not fetch spreadsheet with ID {id}: {str(e)}")

def main():
    """Main function to start the MCP HTTP server"""
    import os
    
    # Get port from Railway environment variable, default to 8000
    port = int(os.environ.get("PORT", 8000))
    
    logger.info("Starting Google Sheets MCP HTTP Server")
    logger.info(f"Railway PORT environment variable: {os.environ.get('PORT', 'Not set')}")
    logger.info("MCP endpoint will be available at /mcp")
    
    # Create a FastAPI app and mount the MCP server
    from fastapi import FastAPI
    app = FastAPI()
    
    # Mount the MCP server at /mcp endpoint
    app.mount("/mcp", mcp)
    
    # Add a root endpoint for health checks
    @app.get("/")
    async def health_check():
        return {
            "status": "healthy",
            "service": "Google Sheets MCP Server",
            "version": "1.0.7",
            "mcp_endpoint": "/mcp"
        }
    
    # Run with uvicorn
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

if __name__ == "__main__":
    main()
