#!/usr/bin/env python
"""
HTTP Server with MCP SSE endpoint for Railway deployment
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn

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

# Global context for the spreadsheet services
spreadsheet_context: SpreadsheetContext = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifespan of the FastAPI app and Google Sheets context"""
    global spreadsheet_context
    logger.info("Starting up Google Sheets MCP Server...")
    
    if SHEETS_AVAILABLE:
        try:
            # Initialize the spreadsheet context
            async with spreadsheet_lifespan(None) as ctx:
                spreadsheet_context = ctx
                logger.info("✅ Google Sheets MCP context initialized")
                yield
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets context: {e}")
            spreadsheet_context = None
            yield
    else:
        logger.warning("Google Sheets components not available - running in limited mode")
        spreadsheet_context = None
        yield
    
    logger.info("Shutting down Google Sheets MCP Server...")

# Create FastAPI app
app = FastAPI(
    title="Google Sheets MCP Server",
    description="MCP server for Google Sheets with ChatGPT connector support",
    version="1.0.2",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Google Sheets MCP Server",
        "version": "1.0.3",
        "sheets_available": SHEETS_AVAILABLE,
        "context_initialized": spreadsheet_context is not None,
        "endpoints": {
            "sse": "/sse/",
            "sse_root": "/sse",
            "search": "/search",
            "fetch": "/fetch",
            "health": "/"
        }
    }

@app.get("/sse/")
async def sse_endpoint():
    """SSE endpoint for ChatGPT connectors"""
    return {
        "message": "Google Sheets MCP Server is running",
        "status": "ready",
        "tools": ["search", "fetch"],
        "transport": "sse",
        "capabilities": {
            "search": True,
            "fetch": True
        }
    }

@app.get("/sse")
async def sse_root():
    """Root SSE endpoint"""
    return {
        "name": "Google Sheets MCP Server",
        "version": "1.0.6",
        "capabilities": {
            "search": True,
            "fetch": True
        },
        "endpoints": {
            "search": "/search",
            "fetch": "/fetch"
        }
    }

@app.post("/search")
async def search_tool(request: dict):
    """Search for spreadsheets"""
    # Handle both direct query string and JSON request body
    if isinstance(request, dict):
        query = request.get("query", "")
    else:
        query = str(request)
    
    if not query or not query.strip():
        return {"results": []}

    try:
        global spreadsheet_context
        if not SHEETS_AVAILABLE:
            raise HTTPException(status_code=503, detail="Google Sheets components not available")
        if not spreadsheet_context:
            raise HTTPException(status_code=503, detail="Spreadsheet context not initialized")
        
        drive_service = spreadsheet_context.drive_service
        
        # Search for spreadsheets in Google Drive
        logger.info(f"Searching Google Drive for query: '{query}'")
        
        # Build search query for spreadsheets
        search_query = f"mimeType='application/vnd.google-apps.spreadsheet' and (name contains '{query}' or fullText contains '{query}')"
        
        # If folder is specified, limit search to that folder
        if spreadsheet_context.folder_id:
            search_query += f" and '{spreadsheet_context.folder_id}' in parents"
        
        # Execute the search
        results = drive_service.files().list(
            q=search_query,
            spaces='drive',
            fields='files(id, name, webViewLink, modifiedTime)',
            orderBy='modifiedTime desc',
            pageSize=10
        ).execute()
        
        files = results.get('files', [])
        
        # Format results for ChatGPT
        formatted_results = []
        for file in files:
            result = {
                "id": file['id'],
                "title": file['name'],
                "url": file.get('webViewLink', f"https://docs.google.com/spreadsheets/d/{file['id']}"),
                "modified": file.get('modifiedTime', '')
            }
            formatted_results.append(result)
        
        logger.info(f"Found {len(formatted_results)} spreadsheets")
        return {"results": formatted_results}
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/fetch")
async def fetch_tool(request: dict):
    """Fetch complete spreadsheet content"""
    # Handle both direct ID string and JSON request body
    if isinstance(request, dict):
        id = request.get("id", "")
    else:
        id = str(request)
    
    if not id:
        raise HTTPException(status_code=400, detail="Spreadsheet ID is required")

    try:
        global spreadsheet_context
        if not SHEETS_AVAILABLE:
            raise HTTPException(status_code=503, detail="Google Sheets components not available")
        if not spreadsheet_context:
            raise HTTPException(status_code=503, detail="Spreadsheet context not initialized")
        
        sheets_service = spreadsheet_context.sheets_service
        drive_service = spreadsheet_context.drive_service
        
        logger.info(f"Fetching spreadsheet content for ID: {id}")
        
        # Get spreadsheet metadata
        spreadsheet = sheets_service.spreadsheets().get(
            spreadsheetId=id,
            fields='properties,sheets(properties,values)'
        ).execute()
        
        # Get file metadata from Drive
        file_info = drive_service.files().get(
            fileId=id,
            fields='name,webViewLink,modifiedTime'
        ).execute()
        
        # Extract spreadsheet title
        title = spreadsheet.get('properties', {}).get('title', file_info.get('name', 'Unknown Spreadsheet'))
        
        # Extract all sheet data
        sheets_data = []
        for sheet in spreadsheet.get('sheets', []):
            sheet_props = sheet.get('properties', {})
            sheet_name = sheet_props.get('title', 'Unknown Sheet')
            
            # Get sheet values
            sheet_values = []
            try:
                values_result = sheets_service.spreadsheets().values().get(
                    spreadsheetId=id,
                    range=sheet_name
                ).execute()
                sheet_values = values_result.get('values', [])
            except Exception as e:
                logger.warning(f"Could not fetch values for sheet {sheet_name}: {e}")
                sheet_values = []
            
            sheets_data.append({
                "name": sheet_name,
                "values": sheet_values
            })
        
        # Create comprehensive result
        result = {
            "id": id,
            "title": title,
            "text": json.dumps({
                "spreadsheet_title": title,
                "sheets": sheets_data,
                "total_sheets": len(sheets_data)
            }, indent=2),
            "url": file_info.get('webViewLink', f"https://docs.google.com/spreadsheets/d/{id}"),
            "metadata": {
                "modified_time": file_info.get('modifiedTime', ''),
                "total_sheets": len(sheets_data),
                "sheet_names": [sheet["name"] for sheet in sheets_data]
            }
        }
        
        logger.info(f"Successfully fetched spreadsheet: {title}")
        return result
        
    except Exception as e:
        logger.error(f"Fetch failed for ID {id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not fetch spreadsheet with ID {id}: {str(e)}")

def main():
    """Main function to start the HTTP server"""
    import os
    
    # Get port from Railway environment variable, default to 8000
    port = int(os.environ.get("PORT", 8000))
    
    logger.info("Starting Google Sheets MCP HTTP Server")
    logger.info(f"Server will be available at http://0.0.0.0:{port}")
    logger.info(f"Railway PORT environment variable: {os.environ.get('PORT', 'Not set')}")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

if __name__ == "__main__":
    main()
