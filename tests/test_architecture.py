"""Deterministic law must stay deterministic: `manu.law` imports nothing that can reason."""

import ast
from pathlib import Path

LAW = Path(__file__).resolve().parents[1] / "src" / "manu" / "law"
ALLOWED_PREFIXES = ("manu.law", "__future__", "dataclasses", "datetime", "typing", "re", "enum")


def test_law_package_imports_only_the_standard_library_and_itself():
    for path in LAW.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.startswith(ALLOWED_PREFIXES), f"{path.name} imports {node.module}"
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.startswith(ALLOWED_PREFIXES), f"{path.name} imports {alias.name}"
