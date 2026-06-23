from __future__ import annotations

import json
import unittest
from datetime import timedelta
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


REPO_ROOT = Path(__file__).resolve().parents[3]


def _json_payload(result) -> dict:
    if getattr(result, "isError", False):
        text = result.content[0].text if result.content else "unknown MCP error"
        raise AssertionError(text)
    if not result.content:
        raise AssertionError("MCP tool returned no content")
    return json.loads(result.content[0].text)


class McpStdioIntegrationTests(unittest.TestCase):
    def test_stdio_server_lists_and_calls_tools_with_mocks(self) -> None:
        async def run_check() -> None:
            server = StdioServerParameters(
                command="python",
                args=["tools/authservice_qa_mcp/launcher.py"],
                cwd=REPO_ROOT,
                env={
                    "AUTHSERVICE_QA_MCP_TEST_MODE": "1",
                    "ALLOWED_CONTAINERS": "auth-service",
                    "TEST_DB_TYPE": "sqlite",
                    "TEST_DB_PATH": "does-not-need-to-exist.sqlite",
                },
            )

            async with stdio_client(server) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    tools = await session.list_tools()
                    self.assertEqual(
                        {tool.name for tool in tools.tools},
                        {"get_container_logs", "query_test_db"},
                    )

                    logs_result = await session.call_tool(
                        "get_container_logs",
                        {"container_name": "auth-service", "lines": 3},
                        read_timeout_seconds=timedelta(seconds=10),
                    )
                    logs = _json_payload(logs_result)
                    self.assertEqual(logs["resolved_container"], "auth-service")
                    self.assertEqual(logs["lines_returned"], 3)

                    db_result = await session.call_tool(
                        "query_test_db",
                        {"sql_query": "SELECT email, status FROM users"},
                        read_timeout_seconds=timedelta(seconds=10),
                    )
                    db = _json_payload(db_result)
                    self.assertEqual(db["database_type"], "mock")
                    self.assertEqual(db["rows"][0]["email"], "test@test.com")

        anyio.run(run_check)


if __name__ == "__main__":
    unittest.main()
