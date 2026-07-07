from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from mythings.ledger import Ledger

from myserver import __version__

# The request/response core is socket-free on purpose: routing and rendering are
# pure functions of a Request, so every endpoint is testable without binding a
# port. server.py is the only place a real socket appears.


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    query: Mapping[str, str]


@dataclass(frozen=True)
class Response:
    status: int
    body: str
    content_type: str = "application/json"


def _json(status: int, payload: object) -> Response:
    return Response(status=status, body=json.dumps(payload, indent=2) + "\n")


def _positive_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        n = int(value)
    except ValueError:
        return default
    return n if n > 0 else default


class App:
    # Read-only over the ledger and repo state. No route mutates anything; the
    # server exists to surface the fleet, never to act on its behalf.
    def __init__(self, ledger: Ledger) -> None:
        self.ledger = ledger

    def handle(self, request: Request) -> Response:
        if request.method != "GET":
            return _json(405, {"error": "read-only server; only GET is allowed"})

        path = request.path.rstrip("/") or "/"
        if path == "/" or path == "/health":
            return self._health()
        if path == "/ledger":
            return self._ledger(request.query)
        return _json(404, {"error": f"no such resource: {request.path}"})

    def _health(self) -> Response:
        return _json(
            200,
            {"status": "ok", "tool": "my-server", "version": __version__},
        )

    def _ledger(self, query: Mapping[str, str]) -> Response:
        tool = query.get("tool")
        kind = query.get("kind")
        limit = _positive_int(query.get("limit"), 50)
        entries = self.ledger.read(tool=tool, kind=kind)
        recent = entries[-limit:]
        return _json(
            200,
            {
                "count": len(recent),
                "total": len(entries),
                "entries": [
                    {
                        "ts": e.ts,
                        "tool": e.tool,
                        "kind": e.kind,
                        "outcome": e.outcome,
                        "detail": e.detail,
                        "data": e.data,
                    }
                    for e in recent
                ],
            },
        )


def build_app(ledger_path: str | Path) -> App:
    return App(Ledger(ledger_path))
