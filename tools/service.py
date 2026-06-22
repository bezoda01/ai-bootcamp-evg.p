#!/usr/bin/env python3
"""
QA Training Tools Service
Provides Claude Code with custom skills for Docker log retrieval and database queries.
"""

import json
import sqlite3
import docker
import argparse
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime, timezone


class DockerLogsProvider:
    """Manages Docker container log retrieval."""

    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            raise RuntimeError(f"Could not connect to Docker: {e}")

    def get_logs(self, container_name: str, lines: int = 50) -> Dict[str, Any]:
        """
        Retrieve the last N lines from a Docker container.

        Args:
            container_name: Name of the container
            lines: Number of lines to retrieve (default: 50)

        Returns:
            Dict with 'success', 'logs', 'container_name', 'error' (if any)
        """
        try:
            container = self.client.containers.get(container_name)

            # Get logs
            logs_bytes = container.logs(tail=lines, timestamps=False)
            logs_text = logs_bytes.decode("utf-8")
            log_lines = logs_text.strip().split("\n") if logs_text.strip() else []

            return {
                "success": True,
                "container_name": container_name,
                "lines_requested": lines,
                "lines_returned": len(log_lines),
                "logs": log_lines,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except docker.errors.NotFound:
            return {
                "success": False,
                "container_name": container_name,
                "error": f"Container '{container_name}' not found",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "container_name": container_name,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def list_containers(self) -> Dict[str, Any]:
        """List all running containers."""
        try:
            containers = self.client.containers.list()
            return {
                "success": True,
                "containers": [
                    {
                        "name": c.name,
                        "id": c.id[:12],
                        "status": c.status,
                        "image": c.image.tags[0] if c.image.tags else c.image.id[:12],
                    }
                    for c in containers
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


class DatabaseQueryProvider:
    """Manages database query execution."""

    def __init__(self, db_path: str = "database.sqlite"):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file not found: {db_path}")

    def query(self, sql_query: str) -> Dict[str, Any]:
        """
        Execute a SELECT query against the database.

        Args:
            sql_query: SQL query (SELECT only, for safety)

        Returns:
            Dict with 'success', 'results', 'columns', 'row_count', 'error' (if any)
        """
        # Safety check: only allow SELECT
        normalized_query = sql_query.strip().upper()
        if not normalized_query.startswith("SELECT"):
            return {
                "success": False,
                "error": "Only SELECT queries are allowed",
                "query": sql_query[:100],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(sql_query)
            rows = cursor.fetchall()

            # Convert rows to list of dicts
            columns = [description[0] for description in cursor.description]
            results = [dict(row) for row in rows]

            conn.close()

            return {
                "success": True,
                "query": sql_query,
                "columns": columns,
                "row_count": len(results),
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except sqlite3.Error as e:
            return {
                "success": False,
                "query": sql_query,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "query": sql_query,
                "error": f"Unexpected error: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def get_schema(self) -> Dict[str, Any]:
        """Get database schema information."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Get all tables
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]

            schema = {}
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                schema[table] = [
                    {
                        "name": col[1],
                        "type": col[2],
                        "notnull": bool(col[3]),
                        "pk": bool(col[5]),
                    }
                    for col in columns
                ]

            conn.close()

            return {
                "success": True,
                "tables": tables,
                "schema": schema,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


class QAToolsService:
    """Main service that combines Docker and Database providers."""

    def __init__(self, db_path: str = "database.sqlite"):
        self.docker = DockerLogsProvider()
        self.db = DatabaseQueryProvider(db_path)

    def handle_request(self, request_type: str, **kwargs) -> Dict[str, Any]:
        """
        Route requests to appropriate handler.

        Args:
            request_type: 'get_container_logs', 'query_test_db', 'list_containers', 'get_schema'
            **kwargs: Arguments for the specific handler

        Returns:
            Response dictionary
        """
        if request_type == "get_container_logs":
            return self.docker.get_logs(
                kwargs.get("container_name"), kwargs.get("lines", 50)
            )
        elif request_type == "query_test_db":
            return self.db.query(kwargs.get("sql_query", ""))
        elif request_type == "list_containers":
            return self.docker.list_containers()
        elif request_type == "get_schema":
            return self.db.get_schema()
        else:
            return {
                "success": False,
                "error": f"Unknown request type: {request_type}",
            }


def main():
    parser = argparse.ArgumentParser(
        description="QA Training Tools Service - Docker logs and database queries"
    )
    parser.add_argument(
        "--db",
        default="database.sqlite",
        help="Path to SQLite database (default: database.sqlite)",
    )
    parser.add_argument(
        "--logs",
        type=int,
        help="Get N lines from container logs",
    )
    parser.add_argument(
        "container_name",
        nargs="?",
        help="Container name (used with --logs)",
    )
    parser.add_argument(
        "--query", help="Execute SELECT query against database"
    )
    parser.add_argument(
        "--containers",
        action="store_true",
        help="List all running containers",
    )
    parser.add_argument(
        "--schema",
        action="store_true",
        help="Show database schema",
    )

    args = parser.parse_args()

    try:
        service = QAToolsService(db_path=args.db)

        if args.containers:
            result = service.docker.list_containers()
            print(json.dumps(result, indent=2))
        elif args.query:
            result = service.db.query(args.query)
            print(json.dumps(result, indent=2))
        elif args.schema:
            result = service.db.get_schema()
            print(json.dumps(result, indent=2))
        elif args.logs and args.container_name:
            result = service.docker.get_logs(args.container_name, args.logs)
            print(json.dumps(result, indent=2))
        else:
            print("Usage: python tools/service.py --help")
            print("\nExamples:")
            print("  python tools/service.py --containers")
            print("  python tools/service.py --schema")
            print("  python tools/service.py --query 'SELECT * FROM users'")
            print("  python tools/service.py --logs 10 auth-service")

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        exit(1)


if __name__ == "__main__":
    main()
