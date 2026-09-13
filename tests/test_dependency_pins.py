from __future__ import annotations

import re
import tomllib
from pathlib import Path

_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _dependencies() -> list[str]:
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    return data["project"]["dependencies"]


def test_mcp_dependency_has_a_floor_and_a_ceiling() -> None:
    deps = _dependencies()
    (mcp_dep,) = [d for d in deps if re.match(r"^mcp\b", d)]
    assert mcp_dep != "mcp", (
        "mcp is unpinned -- an unpinned major version on this fast-moving SDK let CI "
        "resolve mcp 2.x, which dropped Server.list_tools and broke the whole suite "
        "while the local .venv stayed on 1.x and stayed green"
    )
    assert ">=1.28" in mcp_dep
    assert "<2" in mcp_dep


def test_other_dependencies_are_still_present() -> None:
    assert "my-things-core" in _dependencies()
