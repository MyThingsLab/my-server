from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

from mythings.ledger import Ledger

from myserver.app import build_app
from myserver.server import make_server


def _serve_one(tmp_path: Path):
    Ledger(tmp_path / "ledger.jsonl").record(
        tool="my-guard", kind="scan", outcome="success", detail="only"
    )
    app = build_app(tmp_path / "ledger.jsonl")
    httpd = make_server(app, host="127.0.0.1", port=0)  # port 0 → ephemeral
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread


def _fetch(httpd, path: str) -> tuple[int, dict]:
    host, port = httpd.server_address[0], httpd.server_address[1]
    with urllib.request.urlopen(f"http://{host}:{port}{path}", timeout=5) as resp:  # noqa: S310
        return resp.status, json.loads(resp.read())


def test_end_to_end_health_and_ledger(tmp_path: Path) -> None:
    httpd, thread = _serve_one(tmp_path)
    try:
        status, payload = _fetch(httpd, "/health")
        assert status == 200
        assert payload["status"] == "ok"

        status, payload = _fetch(httpd, "/ledger")
        assert status == 200
        assert payload["entries"][0]["detail"] == "only"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def test_end_to_end_enqueue_disabled_without_token(tmp_path: Path) -> None:
    # make_server builds the App with token=None here, so the write surface is off.
    httpd, thread = _serve_one(tmp_path)
    host, port = httpd.server_address[0], httpd.server_address[1]
    try:
        req = urllib.request.Request(
            f"http://{host}:{port}/tools/my-researcher/issues",
            data=b'{"repo":"o/r","title":"t"}',
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)  # noqa: S310
            raise AssertionError("enqueue should be disabled without a token")
        except urllib.error.HTTPError as err:
            assert err.code == 403
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
