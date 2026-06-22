# AuthService QA Skill and MCP Server

This folder contains the portable Skill and MCP server files that should be copied or pushed into the root of the `ai-bootcamp-2` AuthService training application.

The MCP server gives an AI coding agent two tools:

- `get_container_logs(container_name, lines)` - reads the last N log lines from a Docker container or docker-compose service.
- `query_test_db(sql_query)` - runs read-only `SELECT` / read-only `WITH` queries against the configured test database.

The packaged Skill explains when and how an agent should use these tools while debugging AuthService login/API behavior.

## Files Included

```text
.mcp.json
.codex/config.toml
.agents/skills/authservice-debug/SKILL.md
.claude/skills/authservice-debug/SKILL.md
tools/authservice_qa_mcp/
  __init__.py
  config.py
  db_tools.py
  docker_tools.py
  launcher.py
  requirements.txt
  safety.py
  server.py
  tests/
    test_docker_tools.py
    test_mcp_configuration.py
    test_safety.py
```

Not included on purpose:

- `.venv/`
- `__pycache__/`
- `.pyc` files
- local Claude settings such as `.claude/settings.local.json`
- database or log files

## Minimal Requirements

Install these on the machine that will run the app and MCP server:

1. Python 3.10 or newer.
2. Docker Desktop / Docker CLI, available as `docker` in the terminal.
3. The Python MCP SDK from `tools/authservice_qa_mcp/requirements.txt`.

For this AuthService app, the default database mode is local SQLite, so PostgreSQL dependencies are not required.

Optional only if you switch `TEST_DB_TYPE=postgres`:

```powershell
python -m pip install "psycopg[binary]>=3.1"
```

## Where To Put These Files

Put the included files in the root of the `ai-bootcamp-2` repository, next to:

```text
docker-compose.yml
package.json
src/
```

After copying, the repository root should contain:

```text
ai-bootcamp-2/
  .mcp.json
  .codex/
  .agents/
  .claude/
  tools/
  docker-compose.yml
  package.json
  src/
```

## Quick Start On Windows PowerShell

Run these commands from the root of the `ai-bootcamp-2` repository.

1. Install the Node dependencies for the application:

```powershell
npm install
```

2. Initialize the test SQLite database if it does not exist yet:

```powershell
npm run init-db
```

3. Install the MCP server Python dependency:

```powershell
python -m pip install -r tools/authservice_qa_mcp/requirements.txt
```

4. Start the AuthService container:

```powershell
docker compose up -d --build
```

5. Confirm that the container is running:

```powershell
docker ps --format "{{.Names}}"
```

Expected container name:

```text
auth-service
```

6. Run the MCP unit tests:

```powershell
$env:PYTHONPATH = "tools"
python -m unittest discover -s tools/authservice_qa_mcp/tests -v
```

Expected result:

```text
OK
```

7. Optional: run a direct database smoke test:

```powershell
$env:PYTHONPATH = "tools"
@'
from authservice_qa_mcp.config import load_settings
from authservice_qa_mcp.db_tools import query_test_db

settings = load_settings()
print(query_test_db("SELECT id, email, status FROM users ORDER BY id LIMIT 3", settings))
'@ | python -
```

8. Optional: run a direct Docker logs smoke test:

```powershell
$env:PYTHONPATH = "tools"
@'
from authservice_qa_mcp.docker_tools import get_logs

print(get_logs("auth-service", 5, {"auth-service"}))
'@ | python -
```

## MCP Configuration

The Claude Code config is `.mcp.json`:

```json
{
  "mcpServers": {
    "authservice-qa": {
      "type": "stdio",
      "command": "python",
      "args": ["tools/authservice_qa_mcp/launcher.py"],
      "env": {
        "ALLOWED_CONTAINERS": "auth-service",
        "MAX_LOG_LINES": "500",
        "QUERY_MAX_ROWS": "100",
        "QUERY_TIMEOUT_SECONDS": "5",
        "TEST_DB_TYPE": "sqlite",
        "TEST_DB_PATH": "database.sqlite"
      }
    }
  }
}
```

The Codex config is `.codex/config.toml` and points to the same launcher.

The launcher is intentionally repo-relative:

```text
python tools/authservice_qa_mcp/launcher.py
```

This avoids hard-coded local paths such as:

```text
C:\Users\...\tools\.venv\Scripts\python.exe
```

## Skill Locations

Two copies are included because different agent runtimes discover project skills in different folders:

```text
.claude/skills/authservice-debug/SKILL.md
.agents/skills/authservice-debug/SKILL.md
```

The Skill tells the agent to:

1. Reproduce or identify the failing API case.
2. Read Docker logs with `get_container_logs`.
3. Query the test DB with `query_test_db`.
4. Compare API response, `users.status`, and log event/reason.
5. Report the likely root cause and recovery action.

## Tool Details

### get_container_logs

Example tool call:

```text
get_container_logs(container_name="auth-service", lines=100)
```

Behavior:

- Validates the container name.
- Restricts access to `ALLOWED_CONTAINERS` when configured.
- Resolves exact container names and docker-compose service labels.
- Runs Docker through the Docker CLI.
- Does not require the Python Docker SDK.

### query_test_db

Example tool call:

```sql
SELECT id, email, status, created_at
FROM users
WHERE email = 'test@test.com';
```

Behavior:

- Accepts only `SELECT` or read-only `WITH` queries.
- Rejects stacked SQL statements.
- Blocks mutating SQL keywords such as `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `PRAGMA`, and `VACUUM`.
- Opens SQLite in read-only mode where possible.
- Limits output rows with `QUERY_MAX_ROWS`.
- Supports local SQLite by default.

## Environment Variables

The default values are already set in `.mcp.json` and `.codex/config.toml`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `ALLOWED_CONTAINERS` | `auth-service` | Comma-separated allowlist for Docker access. |
| `MAX_LOG_LINES` | `500` | Maximum allowed `lines` value for logs. |
| `QUERY_MAX_ROWS` | `100` | Maximum returned DB rows. |
| `QUERY_TIMEOUT_SECONDS` | `5` | Query timeout. |
| `TEST_DB_TYPE` | `sqlite` | Database mode: `sqlite`, `sqlite-container`, or `postgres`. |
| `TEST_DB_PATH` | `database.sqlite` | SQLite file path relative to the repo root. |
| `SQLITE_CONTAINER_NAME` | `auth-service` | Container used for `sqlite-container` mode. |
| `SQLITE_CONTAINER_PATH` | `/app/database.sqlite` | SQLite path inside the container. |
| `POSTGRES_DSN` | empty | Required only for `TEST_DB_TYPE=postgres`. |

## SQLite Modes

Default local-file mode:

```text
TEST_DB_TYPE=sqlite
TEST_DB_PATH=database.sqlite
```

Container-copy mode:

```text
TEST_DB_TYPE=sqlite-container
SQLITE_CONTAINER_NAME=auth-service
SQLITE_CONTAINER_PATH=/app/database.sqlite
```

The container-copy mode uses `docker cp` to copy the SQLite file to a temporary file and then queries that temporary copy read-only.

## Troubleshooting

### MCP dependency is missing

Install it:

```powershell
python -m pip install -r tools/authservice_qa_mcp/requirements.txt
```

### Docker command is not found

Install Docker Desktop and make sure this command works:

```powershell
docker ps
```

### Container is not found

Start the app:

```powershell
docker compose up -d --build
```

Then verify the name:

```powershell
docker ps --format "{{.Names}}"
```

If the container name is different, update `ALLOWED_CONTAINERS` and call `get_container_logs` with the real name.

### Query is rejected

Only read-only `SELECT` and read-only `WITH` statements are allowed.

Do not use:

```sql
INSERT
UPDATE
DELETE
DROP
ALTER
PRAGMA
VACUUM
```

### Windows Unicode output issues

Use the included launcher:

```text
tools/authservice_qa_mcp/launcher.py
```

It configures stdio as UTF-8 before starting the MCP server.

## Recommended Final Check Before Push

From the repository root:

```powershell
python -m pip install -r tools/authservice_qa_mcp/requirements.txt
$env:PYTHONPATH = "tools"
python -m unittest discover -s tools/authservice_qa_mcp/tests -v
python -m compileall -q tools/authservice_qa_mcp
```

Then start Docker and test the running app if needed:

```powershell
docker compose up -d --build
docker ps --format "{{.Names}}"
```

The MCP server should be ready for an agent after the editor/agent reloads its MCP configuration.
