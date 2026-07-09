from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from myserver.app import App, Request, build_app

# Every tool maps 1:1 to an existing App route (see app.py) -- this module adds
# no business logic of its own, only a JSON-RPC/stdio transport in front of the
# same socket-free App that server.py already wraps over HTTP.
_TOOLS: tuple[types.Tool, ...] = (
    types.Tool(
        name="list_tools",
        description="List the MyThingsLab tools my-server knows about.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="tool_status",
        description="Get one tool's spec (name, backlog label, summary).",
        inputSchema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    ),
    types.Tool(
        name="read_ledger",
        description="Read recent entries from the shared MyThingsLab ledger.",
        inputSchema={
            "type": "object",
            "properties": {
                "tool": {"type": "string", "description": "filter to entries from this tool"},
                "kind": {"type": "string", "description": "filter to entries of this kind"},
                "limit": {"type": "integer", "description": "max entries to return (default 50)"},
            },
        },
    ),
    types.Tool(
        name="enqueue_issue",
        description=(
            "File a labeled backlog issue for a tool to pick up through its own CI loop. "
            "Disabled unless the server was started with MYSERVER_TOKEN set."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "the target tool, e.g. my-researcher"},
                "repo": {"type": "string", "description": "org/repo to file the issue in"},
                "title": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["name", "repo", "title"],
        },
    ),
)


def to_request(name: str, arguments: dict, *, token: str | None) -> Request:
    """Translate one MCP tool call into the Request App.handle() already
    understands. The only tool that needs the token is enqueue_issue -- the
    others map to App's unauthenticated GET routes, same as over plain HTTP."""
    if name == "list_tools":
        return Request(method="GET", path="/tools")
    if name == "tool_status":
        return Request(method="GET", path=f"/tools/{arguments['name']}")
    if name == "read_ledger":
        query = {k: str(v) for k, v in arguments.items() if v is not None}
        return Request(method="GET", path="/ledger", query=query)
    if name == "enqueue_issue":
        headers = {"authorization": f"Bearer {token}"} if token else {}
        body = json.dumps({k: v for k, v in arguments.items() if k != "name"})
        return Request(
            method="POST",
            path=f"/tools/{arguments['name']}/issues",
            headers=headers,
            body=body,
        )
    raise ValueError(f"unknown tool: {name}")


def build_mcp_server(app: App, *, token: str | None) -> Server:
    server: Server = Server("myserver")

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return list(_TOOLS)

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict) -> dict:
        request = to_request(name, arguments, token=token)
        response = app.handle(request)
        # App's own status/body (including its 400/401/403/404 error bodies)
        # is relayed verbatim as the tool result -- no separate MCP error path,
        # so a caller sees the same {"error": ...} shape a REST client would.
        return json.loads(response.body)

    return server


async def _run_stdio(server: Server) -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def serve_mcp(*, ledger_path: str | Path = ".mythings/ledger.jsonl") -> None:
    token = os.environ.get("MYSERVER_TOKEN") or None
    app = build_app(ledger_path, token=token)
    server = build_mcp_server(app, token=token)
    asyncio.run(_run_stdio(server))
