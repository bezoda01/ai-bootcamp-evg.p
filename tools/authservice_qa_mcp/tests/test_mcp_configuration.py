from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


class McpConfigurationTests(unittest.TestCase):
    def test_mcp_config_uses_portable_launcher(self) -> None:
        config = json.loads((REPO_ROOT / ".mcp.json").read_text(encoding="utf-8"))
        server = config["mcpServers"]["authservice-qa"]

        self.assertEqual(server["command"], "python")
        self.assertEqual(server["args"], ["tools/authservice_qa_mcp/launcher.py"])
        self.assertNotIn(".venv", json.dumps(server))
        self.assertNotIn(str(REPO_ROOT), json.dumps(server))


if __name__ == "__main__":
    unittest.main()
