from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from .safety import validate_container_name


def _run_docker(args: list[str]) -> subprocess.CompletedProcess[str]:
    command = ["docker", *args]
    try:
        result = subprocess.run(
            command,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Docker CLI was not found. Install Docker Desktop or add docker to PATH.") from exc

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"Docker command failed: {' '.join(command)}\n{stderr}")
    return result


def _container_allowed(requested_name: str, actual_name: str, allowed_containers: set[str]) -> bool:
    if not allowed_containers:
        return True
    return requested_name in allowed_containers or actual_name in allowed_containers


def _docker_names(args: list[str]) -> list[str]:
    result = _run_docker(args)
    return [line.strip().lstrip("/") for line in result.stdout.splitlines() if line.strip()]


def _inspect_container_name(container_name: str) -> str | None:
    command = ["docker", "inspect", "--type", "container", "--format", "{{.Name}}", container_name]
    try:
        result = subprocess.run(
            command,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Docker CLI was not found. Install Docker Desktop or add docker to PATH.") from exc

    if result.returncode == 0:
        return result.stdout.strip().lstrip("/")

    stderr = result.stderr.strip()
    if "No such object" in stderr or "No such container" in stderr:
        return None

    raise RuntimeError(f"Docker command failed: {' '.join(command)}\n{stderr}")


def _ensure_allowed(requested: str, actual: str, allowed_containers: set[str]) -> str:
    if not _container_allowed(requested, actual, allowed_containers):
        raise PermissionError(f"Container/service {requested!r} resolved to {actual!r}, but it is not allowed.")
    return actual


def resolve_container(container_name: str, allowed_containers: set[str]) -> str:
    """Resolve either a real container name/id or a docker-compose service name."""
    requested = validate_container_name(container_name)

    exact_name = _inspect_container_name(requested)
    if exact_name:
        return _ensure_allowed(requested, exact_name, allowed_containers)

    compose_candidates = _docker_names(
        ["ps", "-a", "--filter", f"label=com.docker.compose.service={requested}", "--format", "{{.Names}}"]
    )
    if len(compose_candidates) == 1:
        return _ensure_allowed(requested, compose_candidates[0], allowed_containers)

    all_names = _docker_names(["ps", "-a", "--format", "{{.Names}}"])
    name_candidates = [name for name in all_names if requested == name or requested in name]
    if len(name_candidates) == 1:
        return _ensure_allowed(requested, name_candidates[0], allowed_containers)

    if len(compose_candidates) > 1 or len(name_candidates) > 1:
        names = sorted({*compose_candidates, *name_candidates})
        raise ValueError(
            f"Container name {requested!r} is ambiguous. Use exact container name. Candidates: {names}"
        )

    raise ValueError(f"Docker container or compose service {requested!r} was not found")


def get_logs(container_name: str, lines: int, allowed_containers: set[str]) -> dict:
    container = resolve_container(container_name, allowed_containers)
    result = _run_docker(["logs", "--tail", str(lines), container])
    text = result.stdout
    if result.stderr:
        separator = "" if not text or text.endswith("\n") else "\n"
        text = f"{text}{separator}{result.stderr}"
    split_lines = text.splitlines()
    return {
        "requested_container": container_name,
        "resolved_container": container,
        "lines_requested": lines,
        "lines_returned": len(split_lines),
        "logs": split_lines,
    }


def copy_file_from_container(container_name: str, container_path: str, allowed_containers: set[str]) -> Path:
    container = resolve_container(container_name, allowed_containers)
    fd, temp_name = tempfile.mkstemp(prefix="authservice-db-", suffix=".sqlite")
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        _run_docker(["cp", f"{container}:{container_path}", str(temp_path)])
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    return temp_path
