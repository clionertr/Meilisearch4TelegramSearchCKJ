"""Simple import-lint guardrails for service-layer boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RULES: dict[str, set[str]] = {
    "src/tg_search/api/routes/config.py": {
        "tg_search.core.meilisearch",
        "tg_search.config.config_store",
    },
    "src/tg_search/core/bot.py": {
        "tg_search.core.meilisearch",
        "tg_search.config.config_store",
    },
}


def _collect_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports


@pytest.mark.parametrize("target_file", sorted(RULES))
def test_presentation_layer_no_direct_infra_imports(target_file: str):
    file_path = PROJECT_ROOT / target_file
    imports = _collect_imports(file_path)
    forbidden = RULES[target_file]

    violations = sorted(forbidden.intersection(imports))
    assert not violations, f"{target_file} has forbidden imports: {violations}"
