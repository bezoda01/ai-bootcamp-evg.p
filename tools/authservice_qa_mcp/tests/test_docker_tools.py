from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from authservice_qa_mcp import docker_tools


class DockerToolsTests(unittest.TestCase):
    def test_resolve_container_uses_docker_cli_without_python_docker_sdk(self) -> None:
        calls: list[list[str]] = []

        def fake_run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            if args[:3] == ["docker", "inspect", "--type"]:
                return subprocess.CompletedProcess(args, 0, stdout="auth-service\n", stderr="")
            raise AssertionError(f"unexpected docker command: {args}")

        with patch("authservice_qa_mcp.docker_tools.subprocess.run", side_effect=fake_run):
            self.assertEqual(docker_tools.resolve_container("auth-service", {"auth-service"}), "auth-service")

        self.assertEqual(calls[0][:4], ["docker", "inspect", "--type", "container"])

    def test_docker_commands_do_not_inherit_mcp_stdin(self) -> None:
        with patch("authservice_qa_mcp.docker_tools.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess(["docker", "ps"], 0, stdout="", stderr="")

            docker_tools._run_docker(["ps"])

        self.assertIs(run.call_args.kwargs["stdin"], subprocess.DEVNULL)

    def test_get_logs_returns_tail_output_lines(self) -> None:
        with (
            patch("authservice_qa_mcp.docker_tools.resolve_container", return_value="auth-service"),
            patch(
                "authservice_qa_mcp.docker_tools._run_docker",
                return_value=subprocess.CompletedProcess(
                    ["docker", "logs"], 0, stdout="line one\nline two\n", stderr=""
                ),
            ) as run_docker,
        ):
            result = docker_tools.get_logs("auth-service", 2, {"auth-service"})

        run_docker.assert_called_once_with(["logs", "--tail", "2", "auth-service"])
        self.assertEqual(result["resolved_container"], "auth-service")
        self.assertEqual(result["logs"], ["line one", "line two"])

    def test_copy_file_from_container_uses_docker_cp(self) -> None:
        with (
            patch("authservice_qa_mcp.docker_tools.resolve_container", return_value="auth-service"),
            patch("authservice_qa_mcp.docker_tools._run_docker") as run_docker,
        ):
            run_docker.return_value = subprocess.CompletedProcess(["docker", "cp"], 0, stdout="", stderr="")
            path = docker_tools.copy_file_from_container("auth-service", "/app/database.sqlite", {"auth-service"})

        try:
            self.assertIsInstance(path, Path)
            self.assertIn("authservice-db-", path.name)
            docker_cp_args = run_docker.call_args.args[0]
            self.assertEqual(docker_cp_args[:2], ["cp", "auth-service:/app/database.sqlite"])
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
