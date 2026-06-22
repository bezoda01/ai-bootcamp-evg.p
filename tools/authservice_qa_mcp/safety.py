from __future__ import annotations

import re
from pathlib import Path


CONTAINER_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")

# Conservative blocklist. Real safety comes from DB read-only mode / read-only user,
# but this prevents obvious accidental destructive commands.
BLOCKED_SQL_TOKENS = {
    "alter",
    "analyze",
    "attach",
    "begin",
    "call",
    "commit",
    "copy",
    "create",
    "delete",
    "detach",
    "do",
    "drop",
    "execute",
    "grant",
    "insert",
    "merge",
    "pragma",
    "reindex",
    "replace",
    "reset",
    "revoke",
    "rollback",
    "set",
    "truncate",
    "update",
    "vacuum",
}


def validate_container_name(container_name: str) -> str:
    name = (container_name or "").strip()
    if not name:
        raise ValueError("container_name is required")
    if not CONTAINER_NAME_RE.match(name):
        raise ValueError(
            "container_name may contain only letters, digits, underscore, dot and dash, "
            "and must start with a letter or digit"
        )
    return name


def validate_lines(lines: int, max_lines: int) -> int:
    try:
        value = int(lines)
    except (TypeError, ValueError) as exc:
        raise ValueError("lines must be an integer") from exc

    if value < 1:
        raise ValueError("lines must be >= 1")
    if value > max_lines:
        raise ValueError(f"lines must be <= {max_lines}")
    return value


def strip_sql_comments(sql: str) -> str:
    # Remove /* ... */ comments.
    without_block = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    # Remove -- comments line by line.
    lines = []
    for line in without_block.splitlines():
        lines.append(re.sub(r"--.*$", "", line))
    return "\n".join(lines)


def normalize_select_sql(sql_query: str, max_sql_length: int) -> str:
    if not isinstance(sql_query, str):
        raise ValueError("sql_query must be a string")

    raw = sql_query.strip()
    if not raw:
        raise ValueError("sql_query is empty")
    if len(raw) > max_sql_length:
        raise ValueError(f"sql_query is too long; max length is {max_sql_length}")

    sql = strip_sql_comments(raw).strip()
    if not sql:
        raise ValueError("sql_query contains only comments")

    # Permit exactly one trailing semicolon, reject stacked statements.
    if ";" in sql.rstrip(";"):
        raise ValueError("Only a single SELECT statement is allowed; semicolon-separated statements are rejected")
    sql = sql.rstrip(";").strip()

    lowered = sql.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError("Only SELECT queries are allowed. Query must start with SELECT or WITH")

    tokens = set(re.findall(r"\b[a-z_][a-z0-9_]*\b", lowered))
    blocked = sorted(tokens & BLOCKED_SQL_TOKENS)
    if blocked:
        raise ValueError(f"Query contains blocked SQL keyword(s): {', '.join(blocked)}")

    return sql


def resolve_project_path(project_dir: Path, configured_path: str) -> Path:
    path = Path(configured_path)
    if not path.is_absolute():
        path = project_dir / path
    return path.resolve()
