#!/usr/bin/env python
"""
MCP Server for Google Sheets - ChatGPT Custom Connector Support

This module provides an MCP server with SSE transport that exposes Google Sheets 
functionality as search/fetch tools for ChatGPT custom connectors.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP, Context

# Import the main MCP server components
from .server import spreadsheet_lifespan, SpreadsheetContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server instructions for ChatGPT
server_instructions = """
This MCP server provides Google Sheets search and document retrieval capabilities
for ChatGPT connectors. Use the search tool to find spreadsheets and sheets
based on keywords, then use the fetch tool to retrieve complete
spreadsheet content and data.
"""

# Initialize the MCP server with lifespan management
mcp = FastMCP("Google Sheets MCP Server", 
              dependencies=["google-auth", "google-auth-oauthlib", "google-api-python-client"],
              lifespan=spreadsheet_lifespan)

@mcp.tool()
async def search(query: str, ctx: Context) -> Dict[str, List[Dict[str, Any]]]:
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

    try:
        # Get the spreadsheet context
        spreadsheet_context = ctx.request_context.lifespan_context
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
            pageSize=10  # Limit results for better performance
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
        return {"results": []}

@mcp.tool()
async def fetch(id: str, ctx: Context) -> Dict[str, Any]:
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

    try:
        # Get the spreadsheet context
        spreadsheet_context = ctx.request_context.lifespan_context
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
        raise ValueError(f"Could not fetch spreadsheet with ID {id}: {str(e)}")

def main():
    """Main function to start the MCP server."""
    logger.info("Starting Google Sheets MCP Server")
    logger.info("Server will be available at http://0.0.0.0:8000/sse/")
    # Run the server with HTTP transport for Railway
    mcp.run(transport="sse", host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
