from __future__ import annotations

import os
import sys
from pathlib import Path


def _prefer_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def main() -> None:
    _prefer_utf8_stdio()

    package_dir = Path(__file__).resolve().parent
    tools_dir = package_dir.parent
    project_dir = tools_dir.parent

    sys.path.insert(0, str(tools_dir))
    os.environ.setdefault("PROJECT_DIR", str(project_dir))

    try:
        from authservice_qa_mcp.server import main as server_main
    except ModuleNotFoundError as exc:
        if exc.name == "mcp":
            requirements = package_dir / "requirements.txt"
            print(
                "Missing MCP dependency. Install it with: "
                f"python -m pip install -r {requirements}",
                file=sys.stderr,
            )
            raise SystemExit(1) from exc
        raise

    server_main()


if __name__ == "__main__":
    main()
