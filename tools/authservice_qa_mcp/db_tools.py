from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from .config import Settings
from .docker_tools import copy_file_from_container
from .safety import normalize_select_sql, resolve_project_path


def _serialize(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bytes):
        return value.hex()
    return str(value)


def _rows_to_result(columns: list[str], rows: list[Any], max_rows: int) -> dict:
    truncated = len(rows) > max_rows
    visible_rows = rows[:max_rows]

    normalized_rows: list[dict[str, Any]] = []
    for row in visible_rows:
        if isinstance(row, dict):
            normalized_rows.append({key: _serialize(value) for key, value in row.items()})
        else:
            normalized_rows.append({columns[i]: _serialize(row[i]) for i in range(len(columns))})

    return {
        "columns": columns,
        "rows": normalized_rows,
        "row_count": len(normalized_rows),
        "truncated": truncated,
        "max_rows": max_rows,
    }


def query_sqlite_file(db_path: Path, sql: str, settings: Settings) -> dict:
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database file not found: {db_path}")

    uri = db_path.as_uri() + "?mode=ro&immutable=1"
    deadline = time.monotonic() + settings.query_timeout_seconds

    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row

    def _progress_handler() -> int:
        return 1 if time.monotonic() > deadline else 0

    try:
        connection.set_progress_handler(_progress_handler, 10_000)
        cursor = connection.execute(sql)
        columns = [description[0] for description in cursor.description or []]
        rows = cursor.fetchmany(settings.query_max_rows + 1)
        return {
            "database_type": "sqlite",
            "database": str(db_path),
            **_rows_to_result(columns, rows, settings.query_max_rows),
        }
    finally:
        connection.close()


def query_postgres(sql: str, settings: Settings) -> dict:
    if not settings.postgres_dsn:
        raise ValueError("POSTGRES_DSN is required when TEST_DB_TYPE=postgres")

    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("psycopg is not installed. Run: pip install 'psycopg[binary]'") from exc

    timeout_ms = settings.query_timeout_seconds * 1000
    with psycopg.connect(settings.postgres_dsn, autocommit=False, row_factory=dict_row) as connection:
        with connection.transaction():
            # Defense in depth. Prefer a DB user that only has SELECT grants.
            connection.execute("SET TRANSACTION READ ONLY")
            connection.execute("SET LOCAL statement_timeout = %s", (f"{timeout_ms}ms",))

            with connection.cursor() as cursor:
                cursor.execute(sql)
                columns = [description.name for description in cursor.description or []]
                rows = cursor.fetchmany(settings.query_max_rows + 1)
                return {
                    "database_type": "postgres",
                    **_rows_to_result(columns, rows, settings.query_max_rows),
                }


def query_test_db(sql_query: str, settings: Settings) -> dict:
    sql = normalize_select_sql(sql_query, settings.max_sql_length)

    if settings.test_db_type == "sqlite":
        db_path = resolve_project_path(settings.project_dir, settings.test_db_path)
        return query_sqlite_file(db_path, sql, settings)

    if settings.test_db_type == "sqlite-container":
        temp_db_path = copy_file_from_container(
            settings.sqlite_container_name,
            settings.sqlite_container_path,
            settings.allowed_containers,
        )
        try:
            result = query_sqlite_file(temp_db_path, sql, settings)
            result["database"] = f"copy of {settings.sqlite_container_name}:{settings.sqlite_container_path}"
            return result
        finally:
            temp_db_path.unlink(missing_ok=True)

    if settings.test_db_type == "postgres":
        return query_postgres(sql, settings)

    raise ValueError(f"Unsupported TEST_DB_TYPE: {settings.test_db_type}")
