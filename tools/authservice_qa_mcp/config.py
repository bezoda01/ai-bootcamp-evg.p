from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _as_int(name: str, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        value = default
    else:
        try:
            value = int(raw)
        except ValueError as exc:
            raise ValueError(f"{name} must be an integer, got {raw!r}") from exc

    if minimum is not None and value < minimum:
        value = minimum
    if maximum is not None and value > maximum:
        value = maximum
    return value


def _split_csv(value: str | None) -> set[str]:
    if not value:
        return set()
    return {part.strip() for part in value.split(",") if part.strip()}


@dataclass(frozen=True)
class Settings:
    project_dir: Path
    allowed_containers: set[str]
    max_log_lines: int
    max_sql_length: int
    query_max_rows: int
    query_timeout_seconds: int

    # sqlite | sqlite-container | postgres
    test_db_type: str

    # For TEST_DB_TYPE=sqlite
    test_db_path: str

    # For TEST_DB_TYPE=sqlite-container
    sqlite_container_name: str
    sqlite_container_path: str

    # For TEST_DB_TYPE=postgres
    postgres_dsn: str


def load_settings() -> Settings:
    project_dir = Path(os.getenv("PROJECT_DIR") or os.getcwd()).resolve()

    test_db_type = (os.getenv("TEST_DB_TYPE") or "sqlite").strip().lower()
    if test_db_type not in {"sqlite", "sqlite-container", "postgres"}:
        raise ValueError("TEST_DB_TYPE must be one of: sqlite, sqlite-container, postgres")

    return Settings(
        project_dir=project_dir,
        allowed_containers=_split_csv(os.getenv("ALLOWED_CONTAINERS")),
        max_log_lines=_as_int("MAX_LOG_LINES", 500, minimum=1, maximum=5000),
        max_sql_length=_as_int("MAX_SQL_LENGTH", 10_000, minimum=100, maximum=100_000),
        query_max_rows=_as_int("QUERY_MAX_ROWS", 100, minimum=1, maximum=10_000),
        query_timeout_seconds=_as_int("QUERY_TIMEOUT_SECONDS", 5, minimum=1, maximum=120),
        test_db_type=test_db_type,
        test_db_path=os.getenv("TEST_DB_PATH") or "database.sqlite",
        sqlite_container_name=os.getenv("SQLITE_CONTAINER_NAME") or "auth-service",
        sqlite_container_path=os.getenv("SQLITE_CONTAINER_PATH") or "/app/database.sqlite",
        postgres_dsn=os.getenv("POSTGRES_DSN") or "",
    )
