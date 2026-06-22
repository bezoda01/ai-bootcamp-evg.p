---
name: authservice-debug
description: Debug this AuthService training app by using the local authservice-qa MCP server to read Docker logs and run read-only SELECT queries against the test database. Use when investigating login failures, unexpected HTTP statuses, blocked users, invalid credentials, or log/database mismatches.
---

# AuthService Debug Skill

Use the `authservice-qa` MCP server packaged with this repository.

If the MCP tools are unavailable, install the server dependency from the project root:

```bash
python -m pip install -r tools/authservice_qa_mcp/requirements.txt
```

The project config starts the server through `tools/authservice_qa_mcp/launcher.py`, so it should not require a repo-local virtualenv path. Docker must be running when reading container logs or copying a SQLite DB from a container.

## Workflow

1. Reproduce or identify the failing API case: email, password, endpoint, expected status, actual status.
2. Inspect logs with `get_container_logs(container_name, lines)`.
   - Default container/service name is `auth-service`.
   - Start with 100-200 lines unless the user asks for more.
3. Inspect the test database with `query_test_db(sql_query)`.
   - Only use SELECT queries.
   - Common query: `SELECT id, email, status, created_at FROM users WHERE email = 'test@test.com'`.
4. Compare three things:
   - API response status/message.
   - `users.status` in the DB.
   - JSON log event/reason, for example `login_success`, `invalid_password`, or `user_blocked`.
5. Report the likely root cause and the recovery action.
   - Blocked test user: `npm run restore-user test@test.com` or docker-compose exec equivalent.
   - Missing DB row: reinitialize DB with `npm run init-db` or check volume/mounts.
   - Invalid password: correct test data or test assertion.

## Safety rules

Never use this skill to mutate the DB. Do not run INSERT, UPDATE, DELETE, DROP, ALTER, PRAGMA, VACUUM, or shell commands that change data. The MCP server enforces SELECT/WITH-only SQL and read-only DB access where possible.
