---
name: run-auth-service
description: Run and test the AuthService microservice with curl-based smoke tests
---

# AuthService Driver

This skill drives the **AuthService** — an educational Node.js/Express authentication microservice running in Docker. The service exposes a `/login` endpoint with various response scenarios for QA testing and AI-driven test automation training.

**Driver shape:** Docker-hosted service + `curl`-based smoke test harness. Paths are relative to the project root (`.claude/skills/run-auth-service/driver.sh` from the repo root).

## Prerequisites

**System packages:** (Already present in Docker container)
- Node.js 20+
- npm 9+
- Docker & Docker Compose
- curl (standard on Linux/macOS/Windows with Git Bash)

**Verify Docker is running:**
```bash
docker ps
```

## Build

No build required — the Docker image is pre-built and the container already running. The service initializes its SQLite database automatically on startup.

**To rebuild the image from scratch:**
```bash
docker-compose up --build
```

**To verify the service started cleanly:**
```bash
docker exec auth-service tail -20 logs/app.log
```

## Run (Agent Path)

Use the driver script to interact with the running service programmatically.

### Smoke Tests (Full Suite)

Run all validation tests in one command:
```bash
bash .claude/skills/run-auth-service/driver.sh smoke
```

**Output:** Passes/fails 5 core scenarios:
1. Health check (200 OK)
2. Successful login (200 with user data)
3. Blocked user returns 403
4. Invalid password returns 401
5. Missing credentials returns 400

Exit code 0 on pass, 1 on failure.

### Individual Commands

**Health check:**
```bash
bash .claude/skills/run-auth-service/driver.sh health
```

**Test login (with custom credentials):**
```bash
bash .claude/skills/run-auth-service/driver.sh login test@test.com password123
bash .claude/skills/run-auth-service/driver.sh login admin@test.com adminpass
```

**View recent logs:**
```bash
bash .claude/skills/run-auth-service/driver.sh logs
```

**Block a user (simulate failure):**
```bash
bash .claude/skills/run-auth-service/driver.sh break test@test.com
```

**Restore a user:**
```bash
bash .claude/skills/run-auth-service/driver.sh restore test@test.com
```

**Verbose smoke tests (with response bodies):**
```bash
bash .claude/skills/run-auth-service/driver.sh verbose
```

## Direct API Calls (curl)

For custom testing scenarios, call the API directly:

**Health check:**
```bash
curl -s http://localhost:3000/health
```

**Login:**
```bash
curl -X POST http://localhost:3000/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@test.com", "password": "password123"}'
```

## Run (Human Path)

View the service in a terminal (follow logs):
```bash
docker-compose logs -f auth-service
```

Stop the service:
```bash
docker-compose down
```

Restart:
```bash
docker-compose up
```

## Test Users

Pre-populated in the database:

| Email | Password | Status |
|-------|----------|--------|
| `test@test.com` | `password123` | active (initially) |
| `blocked@test.com` | `password123` | blocked |
| `admin@test.com` | `adminpass` | active |

## Database Management

Run scripts inside the container to modify state:

**Initialize DB from scratch:**
```bash
docker-compose exec auth-service npm run init-db
```

**Block a user:**
```bash
docker-compose exec auth-service npm run break-user test@test.com
```

**Restore a user:**
```bash
docker-compose exec auth-service npm run restore-user test@test.com
```

## Logs

The service logs all events to `logs/app.log` in JSON format (parsed entries per line).

**View from container:**
```bash
docker exec auth-service tail -50 logs/app.log
```

**Example log entries:**

Successful login:
```json
{"level":30,"time":1781717889000,"event":"login_success","email":"test@test.com","user_id":1}
```

Blocked user attempt:
```json
{"level":40,"time":1781717896633,"event":"login_attempt","email":"blocked@test.com","reason":"user_blocked","status":"blocked"}
```

Invalid password:
```json
{"level":40,"time":1781717911279,"event":"login_attempt","email":"test@test.com","reason":"invalid_password"}
```

## Gotchas

1. **Container must be running** — The driver assumes Docker container `auth-service` is already up. Use `docker ps` to verify. If it's stopped, run `docker-compose up`.

2. **Port 3000 must be available** — The service binds to `localhost:3000`. If something else uses this port, either stop it or modify `docker-compose.yml` and restart.

3. **Logs are inside the container** — Use `docker exec auth-service tail logs/app.log`, not local filesystem access. The `logs/` dir is a Docker volume.

4. **User state persists** — Blocking a user with `driver.sh break` modifies the database and persists across container restarts. Use `driver.sh restore` to undo. Clean reset requires `docker-compose down -v` (deletes volumes) then `docker-compose up --build`.

5. **No email verification** — The service doesn't validate email format; any string works. Test both well-formed (`test@test.com`) and edge cases (`test`, `@`, empty string).

6. **Password hashing is intentionally weak** — Uses SHA256 without salt for educational clarity. Not production-safe.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Could not reach service at http://localhost:3000" | Run `docker ps`. If `auth-service` not listed, start it: `docker-compose up`. If port 3000 in use, modify `docker-compose.yml` port mapping. |
| Smoke tests pass but logs are empty | Logs mount to a Docker volume. Verify with `docker exec auth-service ls -la logs/`. |
| "User already exists" when running init-db twice | The script is idempotent and won't duplicate users. Safe to re-run. |
| Blocked user can still log in after restore | Clear your HTTP client cache or use a fresh curl session. The driver always makes fresh requests. |
| JSON parse errors in log output | Some log lines may be multi-line if they contain stack traces. Use `--raw-output` in tools that parse JSON logs. |
