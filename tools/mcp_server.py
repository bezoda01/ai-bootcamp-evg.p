#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Server for QA Training Tools
This server exposes Docker logs and database query capabilities to Claude Code.
"""

import json
import sys
import asyncio
from typing import Any
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from service import QAToolsService


class MCPServer:
    """Simple MCP server for Claude Code integration."""

    def __init__(self, db_path: str = "database.sqlite"):
        self.service = QAToolsService(db_path=db_path)
        self.tools = self._define_tools()

    def _define_tools(self) -> list:
        """Define available tools for Claude Code."""
        return [
            {
                "name": "get_container_logs",
                "description": "Retrieve the last N lines from a Docker container's logs",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "container_name": {
                            "type": "string",
                            "description": "Name of the Docker container (e.g., 'auth-service')",
                        },
                        "lines": {
                            "type": "integer",
                            "description": "Number of log lines to retrieve (default: 50)",
                            "default": 50,
                        },
                    },
                    "required": ["container_name"],
                },
            },
            {
                "name": "query_test_db",
                "description": "Execute a SELECT query against the SQLite test database",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "sql_query": {
                            "type": "string",
                            "description": "SELECT query to execute (safety: only SELECT allowed)",
                        },
                    },
                    "required": ["sql_query"],
                },
            },
            {
                "name": "list_containers",
                "description": "List all running Docker containers",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "get_database_schema",
                "description": "Get the schema of the test database (tables and columns)",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    def process_request(self, request: dict) -> dict:
        """
        Process an incoming MCP request.

        Args:
            request: MCP request dict with 'method', 'params'

        Returns:
            Response dict with 'result' or 'error'
        """
        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": self.tools,
                    },
                    "serverInfo": {
                        "name": "qa-training-tools",
                        "version": "1.0.0",
                    },
                }
            }

        elif method == "tools/list":
            return {
                "result": {
                    "tools": self.tools,
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_input = params.get("arguments", {})

            if tool_name == "get_container_logs":
                result = self.service.docker.get_logs(
                    tool_input.get("container_name"),
                    tool_input.get("lines", 50),
                )
            elif tool_name == "query_test_db":
                result = self.service.db.query(tool_input.get("sql_query", ""))
            elif tool_name == "list_containers":
                result = self.service.docker.list_containers()
            elif tool_name == "get_database_schema":
                result = self.service.db.get_schema()
            else:
                result = {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}",
                }

            return {
                "result": result,
            }

        else:
            return {
                "error": f"Unknown method: {method}",
            }


async def main():
    """Main entry point - reads stdin, processes requests, writes stdout."""
    db_path = Path(__file__).parent.parent / "database.sqlite"

    server = MCPServer(db_path=str(db_path))

    # Read requests from stdin line by line
    loop = asyncio.get_event_loop()

    def read_and_process():
        try:
            while True:
                line = input()
                if not line.strip():
                    continue

                request = json.loads(line)
                response = server.process_request(request)
                print(json.dumps(response))
                sys.stdout.flush()
        except EOFError:
            pass
        except json.JSONDecodeError as e:
            error_response = {"error": f"Invalid JSON: {e}"}
            print(json.dumps(error_response))
            sys.stdout.flush()
        except Exception as e:
            error_response = {"error": f"Unexpected error: {e}"}
            print(json.dumps(error_response))
            sys.stdout.flush()

    await loop.run_in_executor(None, read_and_process)


if __name__ == "__main__":
    asyncio.run(main())
