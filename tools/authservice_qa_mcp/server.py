from __future__ import annotations

import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import load_settings
from .db_tools import query_test_db as run_query_test_db
from .docker_tools import get_logs
from .safety import validate_lines

# Stdio MCP servers must not write logs to stdout because stdout carries JSON-RPC.
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("authservice_qa_mcp")

mcp = FastMCP("authservice-qa")


@mcp.tool()
def get_container_logs(container_name: str, lines: int) -> dict[str, Any]:
    """Return the last N Docker log lines for a specific container or docker-compose service.

    Use this for AuthService debugging, for example:
    get_container_logs(container_name="auth-service", lines=100)

    The server validates the container name, enforces MAX_LOG_LINES, and optionally checks
    ALLOWED_CONTAINERS from the environment.
    """
    settings = load_settings()
    tail = validate_lines(lines, settings.max_log_lines)
    return get_logs(container_name, tail, settings.allowed_containers)


@mcp.tool()
def query_test_db(sql_query: str) -> dict[str, Any]:
    """Execute a read-only SELECT query against the configured test database.

    Supports:
    - TEST_DB_TYPE=sqlite with TEST_DB_PATH, default database.sqlite under PROJECT_DIR
    - TEST_DB_TYPE=sqlite-container with SQLITE_CONTAINER_NAME and SQLITE_CONTAINER_PATH
    - TEST_DB_TYPE=postgres with POSTGRES_DSN

    Only SELECT / WITH queries are accepted. Mutating SQL keywords are blocked and the DB
    connection is opened in read-only mode where possible.
    """
    settings = load_settings()
    return run_query_test_db(sql_query, settings)


def main() -> None:
    logger.info("Starting authservice-qa MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
