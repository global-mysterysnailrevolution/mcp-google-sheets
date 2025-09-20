#!/usr/bin/env python
"""
HTTP Server for Google Sheets MCP Server
Provides HTTP endpoints for ChatGPT custom connectors integration
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Import the main MCP server components
from .server import mcp, SpreadsheetContext, spreadsheet_lifespan

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class ToolCallRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to call")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")

class ToolCallResponse(BaseModel):
    success: bool = Field(..., description="Whether the tool call was successful")
    result: Any = Field(..., description="Tool execution result")
    error: Optional[str] = Field(None, description="Error message if failed")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Health status")
    version: str = Field("1.0.0", description="Server version")
    tools: List[str] = Field(..., description="Available tools")

# Global context for the spreadsheet service
spreadsheet_context: Optional[SpreadsheetContext] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifespan of the HTTP server and MCP context"""
    global spreadsheet_context
    
    # Initialize the MCP context
    async with spreadsheet_lifespan(mcp) as ctx:
        spreadsheet_context = ctx
        logger.info("✅ Google Sheets MCP context initialized")
        yield
        logger.info("🔄 Google Sheets MCP context cleaned up")

# Create FastAPI app
app = FastAPI(
    title="Google Sheets MCP Server",
    description="HTTP interface for Google Sheets MCP server - ChatGPT custom connector",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store tool definitions for ChatGPT integration
TOOL_DEFINITIONS = {
    "list_spreadsheets": {
        "name": "list_spreadsheets",
        "description": "List all spreadsheets in the configured Google Drive folder",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "create_spreadsheet": {
        "name": "create_spreadsheet", 
        "description": "Create a new Google Spreadsheet",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The title of the new spreadsheet"
                }
            },
            "required": ["title"]
        }
    },
    "get_sheet_data": {
        "name": "get_sheet_data",
        "description": "Get data from a specific sheet in a Google Spreadsheet",
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "The ID of the spreadsheet (found in the URL)"
                },
                "sheet": {
                    "type": "string", 
                    "description": "The name of the sheet"
                },
                "range": {
                    "type": "string",
                    "description": "Optional cell range in A1 notation (e.g., 'A1:C10'). If not provided, gets all data."
                }
            },
            "required": ["spreadsheet_id", "sheet"]
        }
    },
    "update_cells": {
        "name": "update_cells",
        "description": "Update cells in a Google Spreadsheet",
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "The ID of the spreadsheet (found in the URL)"
                },
                "sheet": {
                    "type": "string",
                    "description": "The name of the sheet"
                },
                "range": {
                    "type": "string",
                    "description": "Cell range in A1 notation (e.g., 'A1:C10')"
                },
                "data": {
                    "type": "array",
                    "description": "2D array of values to update",
                    "items": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            },
            "required": ["spreadsheet_id", "sheet", "range", "data"]
        }
    },
    "batch_update_cells": {
        "name": "batch_update_cells",
        "description": "Batch update multiple ranges in a Google Spreadsheet",
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "The ID of the spreadsheet"
                },
                "sheet": {
                    "type": "string",
                    "description": "The name of the sheet"
                },
                "ranges": {
                    "type": "object",
                    "description": "Dictionary mapping range strings to 2D arrays of values"
                }
            },
            "required": ["spreadsheet_id", "sheet", "ranges"]
        }
    },
    "add_rows": {
        "name": "add_rows",
        "description": "Add rows to a sheet in a Google Spreadsheet",
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "The ID of the spreadsheet"
                },
                "sheet": {
                    "type": "string",
                    "description": "The name of the sheet"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of rows to add"
                },
                "start_row": {
                    "type": "integer",
                    "description": "0-based row index to start adding. If not provided, adds at the beginning."
                }
            },
            "required": ["spreadsheet_id", "sheet", "count"]
        }
    },
    "list_sheets": {
        "name": "list_sheets",
        "description": "List all sheets in a Google Spreadsheet",
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "The ID of the spreadsheet"
                }
            },
            "required": ["spreadsheet_id"]
        }
    },
    "create_sheet": {
        "name": "create_sheet",
        "description": "Create a new sheet tab in an existing Google Spreadsheet",
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "The ID of the spreadsheet"
                },
                "title": {
                    "type": "string",
                    "description": "The title for the new sheet"
                }
            },
            "required": ["spreadsheet_id", "title"]
        }
    },
    "share_spreadsheet": {
        "name": "share_spreadsheet",
        "description": "Share a Google Spreadsheet with multiple users via email",
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "The ID of the spreadsheet to share"
                },
                "recipients": {
                    "type": "array",
                    "description": "List of recipients with email and role",
                    "items": {
                        "type": "object",
                        "properties": {
                            "email_address": {"type": "string"},
                            "role": {"type": "string", "enum": ["reader", "commenter", "writer"]}
                        }
                    }
                },
                "send_notification": {
                    "type": "boolean",
                    "description": "Whether to send notification emails"
                }
            },
            "required": ["spreadsheet_id", "recipients"]
        }
    },
    "get_sheet_formulas": {
        "name": "get_sheet_formulas",
        "description": "Get formulas from a specific sheet in a Google Spreadsheet",
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "The ID of the spreadsheet (found in the URL)"
                },
                "sheet": {
                    "type": "string",
                    "description": "The name of the sheet"
                },
                "range": {
                    "type": "string",
                    "description": "Optional cell range in A1 notation (e.g., 'A1:C10'). If not provided, gets all formulas from the sheet."
                }
            },
            "required": ["spreadsheet_id", "sheet"]
        }
    },
    "add_columns": {
        "name": "add_columns",
        "description": "Add columns to a sheet in a Google Spreadsheet",
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "The ID of the spreadsheet"
                },
                "sheet": {
                    "type": "string",
                    "description": "The name of the sheet"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of columns to add"
                },
                "start_column": {
                    "type": "integer",
                    "description": "0-based column index to start adding. If not provided, adds at the beginning."
                }
            },
            "required": ["spreadsheet_id", "sheet", "count"]
        }
    },
    "copy_sheet": {
        "name": "copy_sheet",
        "description": "Copy a sheet from one spreadsheet to another",
        "parameters": {
            "type": "object",
            "properties": {
                "src_spreadsheet": {
                    "type": "string",
                    "description": "Source spreadsheet ID"
                },
                "src_sheet": {
                    "type": "string",
                    "description": "Source sheet name"
                },
                "dst_spreadsheet": {
                    "type": "string",
                    "description": "Destination spreadsheet ID"
                },
                "dst_sheet": {
                    "type": "string",
                    "description": "Destination sheet name"
                }
            },
            "required": ["src_spreadsheet", "src_sheet", "dst_spreadsheet", "dst_sheet"]
        }
    },
    "rename_sheet": {
        "name": "rename_sheet",
        "description": "Rename a sheet in a Google Spreadsheet",
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet": {
                    "type": "string",
                    "description": "Spreadsheet ID"
                },
                "sheet": {
                    "type": "string",
                    "description": "Current sheet name"
                },
                "new_name": {
                    "type": "string",
                    "description": "New sheet name"
                }
            },
            "required": ["spreadsheet", "sheet", "new_name"]
        }
    },
    "get_multiple_sheet_data": {
        "name": "get_multiple_sheet_data",
        "description": "Get data from multiple specific ranges in Google Spreadsheets",
        "parameters": {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "description": "List of query objects with spreadsheet_id, sheet, and range",
                    "items": {
                        "type": "object",
                        "properties": {
                            "spreadsheet_id": {"type": "string"},
                            "sheet": {"type": "string"},
                            "range": {"type": "string"}
                        },
                        "required": ["spreadsheet_id", "sheet", "range"]
                    }
                }
            },
            "required": ["queries"]
        }
    },
    "get_multiple_spreadsheet_summary": {
        "name": "get_multiple_spreadsheet_summary",
        "description": "Get a summary of multiple Google Spreadsheets, including sheet names, headers, and first few rows",
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_ids": {
                    "type": "array",
                    "description": "List of spreadsheet IDs to summarize",
                    "items": {"type": "string"}
                },
                "rows_to_fetch": {
                    "type": "integer",
                    "description": "Number of rows (including header) to fetch for summary (default: 5)"
                }
            },
            "required": ["spreadsheet_ids"]
        }
    }
}

# Mock Context class for HTTP mode
class MockContext:
    def __init__(self, context: SpreadsheetContext):
        self.request_context = MockRequestContext(context)

class MockRequestContext:
    def __init__(self, context: SpreadsheetContext):
        self.lifespan_context = context

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for ChatGPT connectors"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        tools=list(TOOL_DEFINITIONS.keys())
    )

@app.get("/tools")
async def list_tools():
    """List all available tools for ChatGPT integration"""
    return {"tools": list(TOOL_DEFINITIONS.values())}

@app.post("/tools/call", response_model=ToolCallResponse)
async def call_tool(request: ToolCallRequest):
    """Execute a tool call for ChatGPT integration"""
    global spreadsheet_context
    
    if not spreadsheet_context:
        raise HTTPException(status_code=503, detail="Spreadsheet context not initialized")
    
    if request.tool_name not in TOOL_DEFINITIONS:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {request.tool_name}")
    
    try:
        # Get the tool function from the MCP server
        tool_func = None
        for tool in mcp.list_tools():
            if tool.name == request.tool_name:
                tool_func = tool.handler
                break
        
        if not tool_func:
            raise HTTPException(status_code=400, detail=f"Tool function not found: {request.tool_name}")
        
        # Create mock context for the tool call
        mock_ctx = MockContext(spreadsheet_context)
        
        # Execute the tool
        result = tool_func(**request.parameters, ctx=mock_ctx)
        
        return ToolCallResponse(
            success=True,
            result=result
        )
        
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return ToolCallResponse(
            success=False,
            result=None,
            error=str(e)
        )

@app.get("/")
async def root():
    """Root endpoint with basic information"""
    return {
        "service": "Google Sheets MCP Server",
        "version": "1.0.0",
        "description": "HTTP interface for ChatGPT custom connectors",
        "endpoints": {
            "health": "/health",
            "tools": "/tools", 
            "call_tool": "/tools/call"
        }
    }

def main():
    """Run the HTTP server"""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    logger.info(f"🚀 Starting Google Sheets MCP HTTP Server on {host}:{port}")
    
    uvicorn.run(
        "mcp_google_sheets.http_server:app",
        host=host,
        port=port,
        log_level="info",
        reload=False
    )

if __name__ == "__main__":
    main()
