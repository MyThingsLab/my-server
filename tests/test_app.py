from __future__ import annotations

import json
from pathlib import Path

import pytest
from mythings.ledger import Ledger

from myserver import __version__
from myserver.app import Request, build_app


def _seed(tmp_path: Path) -> Path:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger(path)
    ledger.record(tool="my-guard", kind="scan", outcome="success", detail="one")
    ledger.record(tool="my-researcher", kind="research", outcome="success", detail="two")
    ledger.record(tool="my-guard", kind="scan", outcome="failure", detail="three")
    return path


def _get(app, path: str, **query: str):
    resp = app.handle(Request(method="GET", path=path, query=query))
    return resp, json.loads(resp.body)


def test_health(tmp_path: Path) -> None:
    app = build_app(tmp_path / "ledger.jsonl")
    resp, payload = _get(app, "/health")
    assert resp.status == 200
    assert payload == {"status": "ok", "tool": "my-server", "version": __version__}


def test_root_is_health(tmp_path: Path) -> None:
    app = build_app(tmp_path / "ledger.jsonl")
    assert _get(app, "/")[1]["status"] == "ok"


def test_ledger_lists_all(tmp_path: Path) -> None:
    app = build_app(_seed(tmp_path))
    resp, payload = _get(app, "/ledger")
    assert resp.status == 200
    assert payload["total"] == 3
    assert payload["count"] == 3
    assert [e["detail"] for e in payload["entries"]] == ["one", "two", "three"]


def test_ledger_filters_by_tool_and_kind(tmp_path: Path) -> None:
    app = build_app(_seed(tmp_path))
    _, payload = _get(app, "/ledger", tool="my-guard", kind="scan")
    assert payload["total"] == 2
    assert {e["tool"] for e in payload["entries"]} == {"my-guard"}


def test_ledger_limit_returns_most_recent(tmp_path: Path) -> None:
    app = build_app(_seed(tmp_path))
    _, payload = _get(app, "/ledger", limit="1")
    assert payload["count"] == 1
    assert payload["total"] == 3
    assert payload["entries"][0]["detail"] == "three"


def test_ledger_bad_limit_falls_back_to_default(tmp_path: Path) -> None:
    app = build_app(_seed(tmp_path))
    for bad in ("0", "-4", "abc"):
        _, payload = _get(app, "/ledger", limit=bad)
        assert payload["count"] == 3


def test_missing_ledger_is_empty_not_error(tmp_path: Path) -> None:
    app = build_app(tmp_path / "nope.jsonl")
    resp, payload = _get(app, "/ledger")
    assert resp.status == 200
    assert payload == {"count": 0, "total": 0, "entries": []}


def test_unknown_path_404(tmp_path: Path) -> None:
    app = build_app(tmp_path / "ledger.jsonl")
    resp, payload = _get(app, "/nope")
    assert resp.status == 404
    assert "no such resource" in payload["error"]


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_writes_are_rejected(tmp_path: Path, method: str) -> None:
    app = build_app(tmp_path / "ledger.jsonl")
    resp = app.handle(Request(method=method, path="/ledger", query={}))
    assert resp.status == 405
