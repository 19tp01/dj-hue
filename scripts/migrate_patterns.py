#!/usr/bin/env python3
"""Migrate Python pattern files to .pattern text format.

Usage: uv run python scripts/migrate_patterns.py [--dry-run]
"""

import ast
import re
import sys
from pathlib import Path


def extract_decorator_args(decorator_node: ast.Call) -> dict:
    """Extract arguments from @pattern(...) decorator."""
    result = {"name": "", "description": "", "tags": [], "palette": None}

    # Positional args: name, description
    for i, arg in enumerate(decorator_node.args):
        if i == 0 and isinstance(arg, ast.Constant):
            result["name"] = arg.value
        elif i == 1 and isinstance(arg, ast.Constant):
            result["description"] = arg.value

    # Keyword args: tags, palette
    for kw in decorator_node.keywords:
        if kw.arg == "tags" and isinstance(kw.value, ast.List):
            result["tags"] = [
                elt.value for elt in kw.value.elts if isinstance(elt, ast.Constant)
            ]
        elif kw.arg == "palette" and isinstance(kw.value, ast.Constant):
            result["palette"] = kw.value.value
        elif kw.arg == "description" and isinstance(kw.value, ast.Constant):
            result["description"] = kw.value.value

    return result


def extract_function_body(source_lines: list[str], func_node: ast.FunctionDef) -> str:
    """Extract the function body, handling local variables and return statement."""
    # Get the lines of the function body (excluding def line and docstring)
    body_start = func_node.body[0].lineno - 1  # 0-indexed

    # Skip docstring if present
    if (
        isinstance(func_node.body[0], ast.Expr)
        and isinstance(func_node.body[0].value, ast.Constant)
        and isinstance(func_node.body[0].value.value, str)
    ):
        if len(func_node.body) > 1:
            body_start = func_node.body[1].lineno - 1
        else:
            # Function only has a docstring, no actual body
            return ""

    body_end = func_node.end_lineno  # 1-indexed, inclusive

    # Extract body lines
    body_lines = source_lines[body_start:body_end]

    # Find the base indentation (first non-empty line)
    base_indent = 0
    for line in body_lines:
        stripped = line.lstrip()
        if stripped:
            base_indent = len(line) - len(stripped)
            break

    # Remove base indentation from all lines
    dedented_lines = []
    for line in body_lines:
        if line.strip():  # Non-empty line
            dedented_lines.append(line[base_indent:] if len(line) > base_indent else line)
        else:
            dedented_lines.append("")

    body_text = "\n".join(dedented_lines).strip()

    # If it's just a return statement, extract the expression
    if body_text.startswith("return "):
        # Simple case: single return statement
        return body_text[7:].strip()  # Remove "return "
    elif body_text.startswith("return("):
        return body_text[6:].strip()  # Remove "return"

    # Complex case: has local variables before return
    # We need to wrap it so it evaluates to the pattern
    # Use a lambda-like approach: define vars, then return the result
    lines = body_text.split("\n")

    # Find the return statement
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("return "):
            # Replace return with the expression being returned
            expr = stripped[7:].strip()
            lines[i] = expr
            break
        elif stripped.startswith("return("):
            expr = stripped[6:].strip()
            lines[i] = expr
            break

    return "\n".join(lines)


def convert_pattern_file(py_path: Path, dry_run: bool = False) -> list[Path]:
    """Convert a Python pattern file to one or more .pattern files.

    Returns list of created .pattern file paths.
    """
    source = py_path.read_text()
    source_lines = source.split("\n")

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"  ERROR: Syntax error in {py_path}: {e}")
        return []

    created_files = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        # Check for @pattern decorator
        pattern_decorator = None
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == "pattern":
                    pattern_decorator = decorator
                    break

        if pattern_decorator is None:
            continue

        # Extract metadata
        meta = extract_decorator_args(pattern_decorator)
        if not meta["name"]:
            print(f"  WARNING: Skipping function {node.name} - no pattern name found")
            continue

        # Extract body
        body = extract_function_body(source_lines, node)
        if not body:
            print(f"  WARNING: Skipping {meta['name']} - empty body")
            continue

        # Build .pattern file content
        lines = [f"name: {meta['name']}"]
        if meta["description"]:
            lines.append(f"description: {meta['description']}")
        if meta["tags"]:
            lines.append(f"tags: {', '.join(meta['tags'])}")
        if meta["palette"]:
            lines.append(f"palette: {meta['palette']}")
        lines.append("---")
        lines.append(body)

        content = "\n".join(lines) + "\n"

        # Generate filename from pattern name (slugify)
        slug = meta["name"].lower()
        slug = re.sub(r"[^a-z0-9]+", "_", slug)
        slug = slug.strip("_")
        pattern_path = py_path.parent / f"{slug}.pattern"

        # Handle filename collisions
        if pattern_path.exists():
            i = 2
            while True:
                pattern_path = py_path.parent / f"{slug}_{i}.pattern"
                if not pattern_path.exists():
                    break
                i += 1

        if dry_run:
            print(f"  Would create: {pattern_path.name}")
            print(f"    Content preview: {content[:100]}...")
        else:
            pattern_path.write_text(content)
            print(f"  Created: {pattern_path.name}")
            created_files.append(pattern_path)

    return created_files


def main():
    dry_run = "--dry-run" in sys.argv

    patterns_dir = Path(__file__).parent.parent / "patterns"
    if not patterns_dir.exists():
        print(f"ERROR: Patterns directory not found: {patterns_dir}")
        sys.exit(1)

    print(f"Migrating patterns from {patterns_dir}")
    if dry_run:
        print("(DRY RUN - no files will be created)")
    print()

    py_files = sorted(patterns_dir.glob("*.py"))
    if not py_files:
        print("No Python pattern files found.")
        return

    all_created = []
    for py_path in py_files:
        if py_path.name.startswith("_"):
            continue
        print(f"Processing: {py_path.name}")
        created = convert_pattern_file(py_path, dry_run)
        all_created.extend(created)

    print()
    print(f"Migration complete: {len(all_created)} pattern files created")

    if not dry_run and all_created:
        print()
        print("Next steps:")
        print("  1. Verify patterns load: uv run dj-hue")
        print("  2. Delete old Python files: rm patterns/*.py")


if __name__ == "__main__":
    main()
