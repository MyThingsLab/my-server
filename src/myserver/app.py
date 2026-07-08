from __future__ import annotations

import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from mythings.ledger import Ledger

from myserver import __version__
from myserver import registry as registry_mod
from myserver.enqueue import IssueCreator, gh_create_issue, issue_number

# The request/response core is socket-free on purpose: routing and rendering are
# pure functions of a Request, so every endpoint is testable without binding a
# port. server.py is the only place a real socket appears.


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    query: Mapping[str, str] = field(default_factory=dict)
    headers: Mapping[str, str] = field(default_factory=dict)  # keys lower-cased
    body: str = ""


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


def _bearer_ok(headers: Mapping[str, str], token: str) -> bool:
    header = headers.get("authorization", "")
    prefix = "Bearer "
    if not header.startswith(prefix):
        return False
    return hmac.compare_digest(header[len(prefix) :], token)


class App:
    # Read-only over the ledger and repo state, with one deliberate, gated write:
    # POST enqueues a labeled backlog issue. That write needs a bearer token
    # (fail-closed: no token configured → the surface is off) and is recorded to
    # the server's own ledger for audit. It never opens PRs or spends model tokens.
    def __init__(
        self,
        ledger: Ledger,
        *,
        registry: tuple[registry_mod.ToolSpec, ...] = registry_mod.REGISTRY,
        token: str | None = None,
        create_issue: IssueCreator = gh_create_issue,
    ) -> None:
        self.ledger = ledger
        self.registry = registry
        self.token = token
        self.create_issue = create_issue

    def handle(self, request: Request) -> Response:
        if request.method == "GET":
            return self._get(request)
        if request.method == "POST":
            return self._post(request)
        return _json(405, {"error": f"{request.method} not allowed"})

    # ---- GET (read-only) -------------------------------------------------

    def _get(self, request: Request) -> Response:
        path = request.path.rstrip("/") or "/"
        if path in ("/", "/health"):
            return self._health()
        if path == "/ledger":
            return self._ledger(request.query)
        if path == "/tools":
            return _json(200, {"tools": [self._spec_json(s) for s in self.registry]})
        if path.startswith("/tools/"):
            name = path[len("/tools/") :]
            spec = registry_mod.find(name)
            if spec is None or spec not in self.registry:
                return _json(404, {"error": f"no such tool: {name}"})
            return _json(200, self._spec_json(spec))
        return _json(404, {"error": f"no such resource: {request.path}"})

    def _health(self) -> Response:
        return _json(200, {"status": "ok", "tool": "my-server", "version": __version__})

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

    def _spec_json(self, spec: registry_mod.ToolSpec) -> dict[str, str]:
        return {"name": spec.name, "label": spec.label, "summary": spec.summary}

    # ---- POST (one gated write: enqueue) ---------------------------------

    def _post(self, request: Request) -> Response:
        path = request.path.rstrip("/")
        if not (path.startswith("/tools/") and path.endswith("/issues")):
            return _json(404, {"error": f"no such resource: {request.path}"})
        name = path[len("/tools/") : -len("/issues")]
        spec = registry_mod.find(name)
        if spec is None or spec not in self.registry:
            return _json(404, {"error": f"no such tool: {name}"})

        if self.token is None:
            return _json(403, {"error": "enqueue disabled: no MYSERVER_TOKEN configured"})
        if not _bearer_ok(request.headers, self.token):
            return _json(401, {"error": "missing or invalid bearer token"})

        try:
            payload = json.loads(request.body or "{}")
        except (json.JSONDecodeError, ValueError):
            return _json(400, {"error": "body must be a JSON object"})
        if not isinstance(payload, dict):
            return _json(400, {"error": "body must be a JSON object"})

        repo = str(payload.get("repo", "")).strip()
        title = str(payload.get("title", "")).strip()
        if not repo or not title:
            return _json(400, {"error": "repo and title are required"})
        body = str(payload.get("body", ""))

        url = self.create_issue(repo=repo, title=title, body=body, label=spec.label)
        number = issue_number(url)
        self.ledger.record(
            tool="my-server",
            kind="enqueue",
            outcome="success",
            detail=f"enqueued {spec.name} issue in {repo}: {title}",
            target=spec.name,
            label=spec.label,
            repo=repo,
            issue=number,
            url=url,
        )
        return _json(
            201,
            {"tool": spec.name, "label": spec.label, "repo": repo, "issue": number, "url": url},
        )


def build_app(
    ledger_path: str | Path,
    *,
    token: str | None = None,
    create_issue: IssueCreator = gh_create_issue,
) -> App:
    return App(Ledger(ledger_path), token=token, create_issue=create_issue)
