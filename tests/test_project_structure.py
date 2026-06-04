"""Fronteiras de pacotes — base estável sem imports legados."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Árvores que devem usar apenas core / services / db / config / api
_SCAN_ROOTS = ("ui", "api", "services", "db", "main.py", "config")

# Pastas com código congelado ou shims
_ALLOWED_MODULES_IMPORTERS = {
    ROOT / "legacy",
    ROOT / "modules",
    ROOT / "pipelines",
    ROOT / "tests",
}


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for entry in _SCAN_ROOTS:
        path = ROOT / entry
        if path.is_file():
            files.append(path)
            continue
        if not path.is_dir():
            continue
        for py in path.rglob("*.py"):
            if py.name == "__init__.py":
                continue
            files.append(py)
    return files


def _imports_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "modules" or alias.name.startswith("modules."):
                    hits.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "modules" or node.module.startswith("modules."):
                hits.append(node.module)
    return hits


def test_production_tree_does_not_import_modules() -> None:
    offenders: list[str] = []
    for py in _iter_python_files():
        if any(py.is_relative_to(allowed) for allowed in _ALLOWED_MODULES_IMPORTERS):
            continue
        for mod in _imports_modules(py):
            rel = py.relative_to(ROOT)
            offenders.append(f"{rel}: {mod}")
    assert offenders == [], "Use core/ ou services/ em vez de modules/:\n" + "\n".join(
        offenders
    )
