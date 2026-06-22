from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib


REPO_ROOT = Path(__file__).resolve().parents[3]


class McpConfigurationTests(unittest.TestCase):
    def test_claude_mcp_config_uses_portable_launcher(self) -> None:
        config = json.loads((REPO_ROOT / ".mcp.json").read_text(encoding="utf-8"))
        server = config["mcpServers"]["authservice-qa"]

        self.assertEqual(server["command"], "python")
        self.assertEqual(server["args"], ["tools/authservice_qa_mcp/launcher.py"])
        self.assertNotIn(".venv", json.dumps(server))
        self.assertNotIn(str(REPO_ROOT), json.dumps(server))

    def test_codex_mcp_config_uses_portable_launcher(self) -> None:
        config = tomllib.loads((REPO_ROOT / ".codex" / "config.toml").read_text(encoding="utf-8"))
        server = config["mcp_servers"]["authservice-qa"]

        self.assertEqual(server["command"], "python")
        self.assertEqual(server["args"], ["tools/authservice_qa_mcp/launcher.py"])
        self.assertNotIn(".venv", str(server))
        self.assertNotIn(str(REPO_ROOT), str(server))


if __name__ == "__main__":
    unittest.main()
