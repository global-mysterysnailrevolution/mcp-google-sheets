#!/usr/bin/env python
"""
Simple MCP-compatible HTTP server for Railway deployment
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
    description="MCP-compatible server for Google Sheets with ChatGPT connector support",
    version="1.0.8",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Google Sheets MCP Server",
        "version": "1.0.8",
        "sheets_available": SHEETS_AVAILABLE,
        "context_initialized": spreadsheet_context is not None,
        "endpoints": {
            "mcp": "/mcp",
            "search": "/search",
            "fetch": "/fetch",
            "health": "/"
        }
    }

@app.post("/mcp")
async def mcp_endpoint(request: dict):
    """MCP endpoint for ChatGPT connectors - handles InitializeRequest"""
    logger.info(f"MCP endpoint called with request: {request}")
    
    # Handle MCP InitializeRequest
    if request.get("jsonrpc") == "2.0" and request.get("method") == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {
                        "listChanged": True
                    },
                    "resources": {
                        "subscribe": True,
                        "listChanged": True
                    }
                },
                "serverInfo": {
                    "name": "Google Sheets MCP Server",
                    "version": "1.0.8"
                }
            }
        }
    
    # Handle tool calls
    if request.get("jsonrpc") == "2.0" and request.get("method") == "tools/call":
        tool_name = request.get("params", {}).get("name")
        tool_args = request.get("params", {}).get("arguments", {})
        
        if tool_name == "search":
            query = tool_args.get("query", "")
            result = await search_tool(query)
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
        elif tool_name == "fetch":
            id = tool_args.get("id", "")
            result = await fetch_tool(id)
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
    
    # Handle tools/list
    if request.get("jsonrpc") == "2.0" and request.get("method") == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "tools": [
                    {
                        "name": "search",
                        "description": "Search for spreadsheets and sheets using Google Sheets API",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Search query string. Natural language queries work best."
                                }
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "fetch",
                        "description": "Retrieve complete spreadsheet content by ID for detailed analysis",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "Spreadsheet ID from Google Sheets (found in the URL)"
                                }
                            },
                            "required": ["id"]
                        }
                    }
                ]
            }
        }
    
    # Default response
    return {
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "error": {
            "code": -32601,
            "message": "Method not found"
        }
    }

async def search_tool(query: str) -> Dict[str, List[Dict[str, Any]]]:
    """Search for spreadsheets"""
    if not query or not query.strip():
        return {"results": []}

    if not SHEETS_AVAILABLE:
        return {"results": [], "error": "Google Sheets components not available"}

    try:
        global spreadsheet_context
        if not spreadsheet_context:
            return {"results": [], "error": "Spreadsheet context not initialized"}
        
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
        return {"results": [], "error": f"Search failed: {str(e)}"}

async def fetch_tool(id: str) -> Dict[str, Any]:
    """Fetch complete spreadsheet content"""
    if not id:
        return {"error": "Spreadsheet ID is required"}

    if not SHEETS_AVAILABLE:
        return {
            "id": id,
            "title": "Placeholder Spreadsheet",
            "text": "Google Sheets integration in progress",
            "url": f"https://docs.google.com/spreadsheets/d/{id}",
            "error": "Google Sheets components not available"
        }

    try:
        global spreadsheet_context
        if not spreadsheet_context:
            return {"error": "Spreadsheet context not initialized"}
        
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
        return {"error": f"Could not fetch spreadsheet with ID {id}: {str(e)}"}

@app.post("/search")
async def search_endpoint(request: dict):
    """Direct search endpoint"""
    query = request.get("query", "")
    result = await search_tool(query)
    return result

@app.post("/fetch")
async def fetch_endpoint(request: dict):
    """Direct fetch endpoint"""
    id = request.get("id", "")
    result = await fetch_tool(id)
    return result

def main():
    """Main function to start the HTTP server"""
    import os
    
    # Get port from Railway environment variable, default to 8000
    port = int(os.environ.get("PORT", 8000))
    
    logger.info("Starting Google Sheets MCP HTTP Server")
    logger.info(f"Server will be available at http://0.0.0.0:{port}")
    logger.info(f"Railway PORT environment variable: {os.environ.get('PORT', 'Not set')}")
    logger.info("MCP endpoint available at /mcp")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

if __name__ == "__main__":
    main()
