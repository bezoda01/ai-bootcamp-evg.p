"""
QA Training Tools
================

Custom tools for Claude Code integration with Docker log retrieval
and database query capabilities.

Available classes:
    - DockerLogsProvider: Docker container log management
    - DatabaseQueryProvider: SQLite database query execution
    - QAToolsService: Main service combining both providers
    - MCPServer: MCP (Model Context Protocol) server for Claude Code

Usage:
    from tools.service import QAToolsService

    service = QAToolsService()
    logs = service.docker.get_logs("auth-service", 50)
    results = service.db.query("SELECT * FROM users")
"""

__version__ = "1.0.0"
__author__ = "QA Training Team"
__all__ = [
    "DockerLogsProvider",
    "DatabaseQueryProvider",
    "QAToolsService",
]

from .service import (
    DockerLogsProvider,
    DatabaseQueryProvider,
    QAToolsService,
)

__all__.extend([
    "DockerLogsProvider",
    "DatabaseQueryProvider",
    "QAToolsService",
])
