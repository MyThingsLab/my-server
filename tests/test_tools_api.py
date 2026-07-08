from __future__ import annotations

import json
from pathlib import Path

from mythings.ledger import Ledger

from myserver.app import App, Request
from myserver.registry import REGISTRY

_ISSUE_URL = "https://github.com/MyThingsLab/my-things-core/issues/42"


class FakeCreator:
    # Mocks the one write boundary (gh issue create). Records its calls.
    def __init__(self, url: str = _ISSUE_URL) -> None:
        self.url = url
        self.calls: list[dict[str, str]] = []

    def __call__(self, *, repo: str, title: str, body: str, label: str) -> str:
        self.calls.append({"repo": repo, "title": title, "body": body, "label": label})
        return self.url


def _app(tmp_path: Path, *, token: str | None = None, creator: FakeCreator | None = None) -> App:
    return App(
        Ledger(tmp_path / "ledger.jsonl"),
        token=token,
        create_issue=creator or FakeCreator(),
    )


def _req(method: str, path: str, *, headers=None, body: str = "") -> Request:
    return Request(method=method, path=path, headers=headers or {}, body=body)


def test_list_tools(tmp_path: Path) -> None:
    resp = _app(tmp_path).handle(_req("GET", "/tools"))
    assert resp.status == 200
    names = {t["name"] for t in json.loads(resp.body)["tools"]}
    assert names == {s.name for s in REGISTRY}


def test_get_one_tool(tmp_path: Path) -> None:
    resp = _app(tmp_path).handle(_req("GET", "/tools/my-researcher"))
    assert resp.status == 200
    assert json.loads(resp.body)["label"] == "my-researcher"


def test_get_unknown_tool_404(tmp_path: Path) -> None:
    assert _app(tmp_path).handle(_req("GET", "/tools/nope")).status == 404


def test_enqueue_disabled_when_no_token(tmp_path: Path) -> None:
    resp = _app(tmp_path, token=None).handle(
        _req("POST", "/tools/my-researcher/issues", body='{"repo":"o/r","title":"t"}')
    )
    assert resp.status == 403


def test_enqueue_requires_bearer(tmp_path: Path) -> None:
    resp = _app(tmp_path, token="secret").handle(
        _req("POST", "/tools/my-researcher/issues", body='{"repo":"o/r","title":"t"}')
    )
    assert resp.status == 401


def test_enqueue_rejects_wrong_token(tmp_path: Path) -> None:
    resp = _app(tmp_path, token="secret").handle(
        _req(
            "POST",
            "/tools/my-researcher/issues",
            headers={"authorization": "Bearer nope"},
            body='{"repo":"o/r","title":"t"}',
        )
    )
    assert resp.status == 401


def test_enqueue_requires_repo_and_title(tmp_path: Path) -> None:
    app = _app(tmp_path, token="secret")
    resp = app.handle(
        _req(
            "POST",
            "/tools/my-researcher/issues",
            headers={"authorization": "Bearer secret"},
            body='{"repo":"o/r"}',
        )
    )
    assert resp.status == 400


def test_enqueue_rejects_bad_json(tmp_path: Path) -> None:
    app = _app(tmp_path, token="secret")
    resp = app.handle(
        _req(
            "POST",
            "/tools/my-researcher/issues",
            headers={"authorization": "Bearer secret"},
            body="not json",
        )
    )
    assert resp.status == 400


def test_enqueue_unknown_tool_404(tmp_path: Path) -> None:
    app = _app(tmp_path, token="secret")
    resp = app.handle(
        _req(
            "POST",
            "/tools/nope/issues",
            headers={"authorization": "Bearer secret"},
            body='{"repo":"o/r","title":"t"}',
        )
    )
    assert resp.status == 404


def test_enqueue_success_creates_labeled_issue_and_records(tmp_path: Path) -> None:
    creator = FakeCreator(url="https://github.com/MyThingsLab/my-things-core/issues/7")
    ledger_path = tmp_path / "ledger.jsonl"
    app = App(Ledger(ledger_path), token="secret", create_issue=creator)
    resp = app.handle(
        _req(
            "POST",
            "/tools/my-researcher/issues",
            headers={"authorization": "Bearer secret"},
            body='{"repo":"MyThingsLab/my-things-core","title":"Study GNNs","body":"depth"}',
        )
    )
    assert resp.status == 201
    payload = json.loads(resp.body)
    assert payload == {
        "tool": "my-researcher",
        "label": "my-researcher",
        "repo": "MyThingsLab/my-things-core",
        "issue": 7,
        "url": "https://github.com/MyThingsLab/my-things-core/issues/7",
    }
    assert creator.calls == [
        {
            "repo": "MyThingsLab/my-things-core",
            "title": "Study GNNs",
            "body": "depth",
            "label": "my-researcher",
        }
    ]
    recorded = Ledger(ledger_path).read(tool="my-server", kind="enqueue")
    assert len(recorded) == 1
    assert recorded[0].data["issue"] == 7


def test_post_to_non_enqueue_path_404(tmp_path: Path) -> None:
    resp = _app(tmp_path, token="secret").handle(_req("POST", "/ledger"))
    assert resp.status == 404
