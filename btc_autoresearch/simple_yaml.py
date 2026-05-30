from __future__ import annotations

from pathlib import Path
from typing import Any


def load_yaml(path: str | Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        with Path(path).open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except ModuleNotFoundError:
        return parse_simple_yaml(Path(path).read_text(encoding="utf-8"))


def dump_yaml(payload: dict[str, Any]) -> str:
    try:
        import yaml  # type: ignore

        return yaml.safe_dump(payload, sort_keys=False)
    except ModuleNotFoundError:
        return dump_simple_yaml(payload)


def parse_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any] | list[Any]]] = [(-1, root)]
    pending_key: tuple[int, dict[str, Any], str] | None = None

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if line.startswith("- "):
            value = parse_scalar(line[2:])
            if pending_key and pending_key[0] == indent - 2:
                _indent, owner, key = pending_key
                owner[key] = []
                parent = owner[key]
                stack.append((indent - 2, parent))
                pending_key = None
            if not isinstance(parent, list):
                raise ValueError(f"List item without list parent: {raw_line}")
            parent.append(value)
            continue

        key, _, value_text = line.partition(":")
        key = key.strip()
        if not value_text.strip():
            child: dict[str, Any] = {}
            if not isinstance(parent, dict):
                raise ValueError(f"Mapping item without mapping parent: {raw_line}")
            parent[key] = child
            stack.append((indent, child))
            pending_key = (indent, parent, key)
        else:
            if not isinstance(parent, dict):
                raise ValueError(f"Mapping item without mapping parent: {raw_line}")
            parent[key] = parse_scalar(value_text.strip())
            pending_key = None
    return root


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in ("true", "false"):
        return value == "true"
    if value in ("null", "~"):
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def dump_simple_yaml(payload: dict[str, Any], indent: int = 0) -> str:
    lines: list[str] = []
    prefix = " " * indent
    for key, value in payload.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(dump_simple_yaml(value, indent + 2))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                lines.append(f"{prefix}  - {item}")
        else:
            lines.append(f"{prefix}{key}: {value}")
    return "\n".join(lines)
