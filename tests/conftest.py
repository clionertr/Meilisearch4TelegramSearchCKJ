"""Global pytest configuration.

Keep this file free of product-specific environment mutation.
Use per-scope conftest files for test-layer setup.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Force local `src/` package resolution for src-layout project.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _PROJECT_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: fast tests without external services")
    config.addinivalue_line("markers", "integration: tests that need external services")
    config.addinivalue_line("markers", "e2e: end-to-end integration tests")
    config.addinivalue_line("markers", "meili: tests requiring real MeiliSearch")


def pytest_collection_modifyitems(items):
    """Auto-tag tests by path to keep marker usage consistent during migration."""
    for item in items:
        path = Path(str(item.fspath))
        parts = path.parts
        if "tests" not in parts:
            continue

        if "integration" in parts:
            item.add_marker("integration")
        elif "unit" in parts:
            item.add_marker("unit")
