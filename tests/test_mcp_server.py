from __future__ import annotations

import asyncio
import json
from pathlib import Path

import mcp.types as types
import pytest
from mythings.ledger import Ledger

from myserver.app import build_app
from myserver.mcp_server import build_mcp_server, to_request

_ISSUE_URL = "https://github.com/MyThingsLab/my-things-core/issues/42"


class FakeCreator:
    def __init__(self, url: str = _ISSUE_URL) -> None:
        self.url = url
        self.calls: list[dict[str, str]] = []

    def __call__(self, *, repo: str, title: str, body: str, label: str) -> str:
        self.calls.append({"repo": repo, "title": title, "body": body, "label": label})
        return self.url


def _seed(tmp_path: Path) -> Path:
    path = tmp_path / "ledger.jsonl"
    Ledger(path).record(tool="my-guard", kind="scan", outcome="success", detail="one")
    return path


async def _call(server, name: str, arguments: dict) -> types.CallToolResult:
    handler = server.request_handlers[types.CallToolRequest]
    req = types.CallToolRequest(
        method="tools/call", params=types.CallToolRequestParams(name=name, arguments=arguments)
    )
    result = await handler(req)
    return result.root


# ---- to_request: pure translation, no App/asyncio involved -----------------


def test_to_request_list_tools() -> None:
    req = to_request("list_tools", {}, token=None)
    assert (req.method, req.path) == ("GET", "/tools")


def test_to_request_tool_status() -> None:
    req = to_request("tool_status", {"name": "my-researcher"}, token=None)
    assert (req.method, req.path) == ("GET", "/tools/my-researcher")


def test_to_request_read_ledger_drops_none_filters() -> None:
    req = to_request("read_ledger", {"tool": "my-guard", "kind": None, "limit": 5}, token=None)
    assert req.method == "GET"
    assert req.path == "/ledger"
    assert req.query == {"tool": "my-guard", "limit": "5"}


def test_to_request_enqueue_issue_carries_bearer_token() -> None:
    req = to_request(
        "enqueue_issue",
        {"name": "my-researcher", "repo": "o/r", "title": "t"},
        token="secret",
    )
    assert req.method == "POST"
    assert req.path == "/tools/my-researcher/issues"
    assert req.headers == {"authorization": "Bearer secret"}
    assert json.loads(req.body) == {"repo": "o/r", "title": "t"}


def test_to_request_enqueue_issue_no_token_no_header() -> None:
    req = to_request("enqueue_issue", {"name": "x", "repo": "o/r", "title": "t"}, token=None)
    assert req.headers == {}


def test_to_request_unknown_tool_raises() -> None:
    with pytest.raises(ValueError, match="unknown tool"):
        to_request("nope", {}, token=None)


# ---- build_mcp_server: end-to-end through App.handle ------------------------


def test_list_tools_registers_the_four_tools(tmp_path: Path) -> None:
    server = build_mcp_server(build_app(tmp_path / "ledger.jsonl"), token=None)
    handler = server.request_handlers[types.ListToolsRequest]
    result = asyncio.run(handler(types.ListToolsRequest(method="tools/list")))
    assert {t.name for t in result.root.tools} == {
        "list_tools", "tool_status", "read_ledger", "enqueue_issue",
    }


def test_call_read_ledger_relays_app_response(tmp_path: Path) -> None:
    server = build_mcp_server(build_app(_seed(tmp_path)), token=None)
    result = asyncio.run(_call(server, "read_ledger", {}))
    assert result.structuredContent["entries"][0]["detail"] == "one"


def test_call_tool_status_unknown_name_relays_404_body(tmp_path: Path) -> None:
    server = build_mcp_server(build_app(tmp_path / "ledger.jsonl"), token=None)
    result = asyncio.run(_call(server, "tool_status", {"name": "not-a-tool"}))
    assert result.structuredContent == {"error": "no such tool: not-a-tool"}


def test_call_enqueue_issue_disabled_without_token(tmp_path: Path) -> None:
    server = build_mcp_server(build_app(tmp_path / "ledger.jsonl", token=None), token=None)
    result = asyncio.run(
        _call(server, "enqueue_issue", {"name": "my-researcher", "repo": "o/r", "title": "t"})
    )
    assert "disabled" in result.structuredContent["error"]


def test_call_enqueue_issue_with_token_creates_issue(tmp_path: Path) -> None:
    creator = FakeCreator()
    app = build_app(tmp_path / "ledger.jsonl", token="secret", create_issue=creator)
    server = build_mcp_server(app, token="secret")

    result = asyncio.run(
        _call(server, "enqueue_issue", {"name": "my-researcher", "repo": "o/r", "title": "t"})
    )

    assert result.structuredContent["issue"] == 42
    assert creator.calls == [{"repo": "o/r", "title": "t", "body": "", "label": "my-researcher"}]
