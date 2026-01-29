"""
Pattern loader for .pattern text files.

Loads patterns from a user-specified patterns directory.
Pattern files use a simple text format with YAML-like header and DSL body.

Format:
    name: Pattern Name
    description: Description here
    tags: tag1, tag2
    palette: palette_name
    ---
    light("all").color("red")
"""

import ast
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .strudel import LightPattern


def load_patterns(
    patterns_dir: Path | None = None,
) -> dict[str, tuple["LightPattern", str, str | None, list[str], str]]:
    """
    Load all patterns from directory.

    Args:
        patterns_dir: Directory containing .pattern files

    Returns:
        Dict mapping pattern name to (LightPattern, description, default_palette, tags, category).
    """
    result: dict[str, tuple["LightPattern", str, str | None, list[str], str]] = {}

    if patterns_dir is None or not patterns_dir.exists():
        return result

    for pattern_file in sorted(patterns_dir.glob("**/*.pattern")):
        if pattern_file.name.startswith("_"):
            continue
        try:
            name, pattern, description, palette, tags, category = _load_pattern_file(pattern_file)
            result[name] = (pattern, description, palette, tags, category)
        except Exception as e:
            print(f"Warning: Failed to load {pattern_file}: {e}")

    return result


def reload_patterns(
    patterns_dir: Path | None = None,
) -> dict[str, tuple["LightPattern", str, str | None, list[str], str]]:
    """
    Reload all patterns (for hot-reload).

    Since we don't cache modules anymore, this is the same as load_patterns.
    """
    return load_patterns(patterns_dir)


def _load_pattern_file(
    file_path: Path,
) -> tuple[str, "LightPattern", str, str | None, list[str], str]:
    """
    Load a single .pattern file.

    Returns:
        (name, pattern, description, palette, tags, category)
    """
    from . import strudel

    text = file_path.read_text()

    # Split header and body
    if "---" not in text:
        raise ValueError("Missing '---' separator between header and body")

    header_text, body = text.split("---", 1)
    body = body.strip()

    if not body:
        raise ValueError("Empty pattern body")

    # Parse header
    meta = _parse_header(header_text)
    name = meta.get("name")
    if not name:
        raise ValueError("Missing 'name' in header")

    # Build namespace with all strudel exports
    namespace = {n: getattr(strudel, n) for n in strudel.__all__}

    # Execute body and capture result
    pattern = _execute_pattern_body(body, namespace)

    return (
        name,
        pattern,
        meta.get("description", ""),
        meta.get("palette"),
        meta.get("tags", []),
        meta.get("category", "Chill"),  # Default to Chill if missing
    )


def _parse_header(header_text: str) -> dict:
    """Parse YAML-like header into dict."""
    result: dict = {}

    for line in header_text.strip().split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()

        if key == "tags":
            # Parse comma-separated tags
            result["tags"] = [t.strip() for t in value.split(",") if t.strip()]
        else:
            result[key] = value

    return result


def _execute_pattern_body(body: str, namespace: dict) -> "LightPattern":
    """
    Execute pattern body and return the resulting LightPattern.

    Handles both simple expressions and multi-statement bodies.
    """
    # Parse as Python code
    try:
        tree = ast.parse(body, mode="exec")
    except SyntaxError as e:
        raise ValueError(f"Syntax error in pattern: {e}")

    if not tree.body:
        raise ValueError("Empty pattern body")

    # If the last statement is an expression, wrap it to capture the result
    last_stmt = tree.body[-1]
    if isinstance(last_stmt, ast.Expr):
        # Convert the expression to an assignment: _result = <expr>
        assign = ast.Assign(
            targets=[ast.Name(id="_result", ctx=ast.Store())],
            value=last_stmt.value,
        )
        # Copy location info from the original expression
        ast.copy_location(assign, last_stmt)
        tree.body[-1] = assign
        ast.fix_missing_locations(tree)

    # Execute the code
    exec(compile(tree, "<pattern>", "exec"), namespace)

    # Get the result
    pattern = namespace.get("_result")
    if pattern is None:
        raise ValueError("Pattern body did not produce a result")

    return pattern


def save_pattern(
    file_path: Path,
    name: str,
    body: str,
    description: str = "",
    tags: list[str] | None = None,
    palette: str | None = None,
    category: str = "Chill",
) -> None:
    """
    Save a pattern to a .pattern file.

    Args:
        file_path: Path to write to
        name: Pattern name
        body: Pattern DSL code
        description: Optional description
        tags: Optional list of tags
        palette: Optional default palette name
        category: Pattern category (Ambient, Buildup, Chill, Upbeat)
    """
    lines = [f"name: {name}"]
    lines.append(f"category: {category}")
    if description:
        lines.append(f"description: {description}")
    if tags:
        lines.append(f"tags: {', '.join(tags)}")
    if palette:
        lines.append(f"palette: {palette}")
    lines.append("---")
    lines.append(body)

    file_path.write_text("\n".join(lines) + "\n")


def get_pattern_source(file_path: Path) -> dict:
    """
    Read a pattern file and return its components.

    Returns:
        Dict with keys: name, description, tags, palette, category, body
    """
    text = file_path.read_text()

    if "---" not in text:
        raise ValueError("Missing '---' separator")

    header_text, body = text.split("---", 1)
    meta = _parse_header(header_text)

    return {
        "name": meta.get("name", ""),
        "description": meta.get("description", ""),
        "tags": meta.get("tags", []),
        "palette": meta.get("palette"),
        "category": meta.get("category", "Chill"),
        "body": body.strip(),
    }
