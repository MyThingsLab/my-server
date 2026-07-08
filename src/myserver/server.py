from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from mythings.ledger import Ledger

from myserver.app import App, Request, build_app


class _Handler(BaseHTTPRequestHandler):
    app: App  # bound per-server below

    # BaseHTTPRequestHandler dispatches to do_<METHOD>; route every verb through
    # the App so the read-only 405 it defines is the response callers actually get
    # (an undefined verb would otherwise short-circuit to a bare 501 upstream).
    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def do_PUT(self) -> None:  # noqa: N802
        self._dispatch("PUT")

    def do_DELETE(self) -> None:  # noqa: N802
        self._dispatch("DELETE")

    def do_PATCH(self) -> None:  # noqa: N802
        self._dispatch("PATCH")

    def _dispatch(self, method: str) -> None:
        parts = urlsplit(self.path)
        query = dict(parse_qsl(parts.query))
        headers = {k.lower(): v for k, v in self.headers.items()}
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8") if length else ""
        response = self.app.handle(
            Request(method=method, path=parts.path, query=query, headers=headers, body=body)
        )
        payload = response.body.encode("utf-8")
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args: object) -> None:  # keep stderr quiet; ledger is the record
        pass


def make_server(app: App, *, host: str, port: int) -> ThreadingHTTPServer:
    handler = type("_BoundHandler", (_Handler,), {"app": app})
    return ThreadingHTTPServer((host, port), handler)


def serve(
    *,
    host: str = "127.0.0.1",
    port: int = 8787,
    ledger_path: str | Path = ".mythings/ledger.jsonl",
) -> None:
    token = os.environ.get("MYSERVER_TOKEN") or None
    app = build_app(ledger_path, token=token)
    httpd = make_server(app, host=host, port=port)
    bound_host, bound_port = httpd.server_address[0], httpd.server_address[1]
    enqueue_state = "enabled" if token else "disabled (set MYSERVER_TOKEN to enable)"

    Ledger(ledger_path).record(
        tool="my-server",
        kind="serve",
        outcome="success",
        detail=f"listening on http://{bound_host}:{bound_port}",
        host=str(bound_host),
        port=bound_port,
    )
    print(
        f"my-server listening on http://{bound_host}:{bound_port} "
        f"— enqueue {enqueue_state} (Ctrl-C to stop)"
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.shutdown()
        httpd.server_close()
