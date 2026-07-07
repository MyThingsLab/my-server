from __future__ import annotations

from pathlib import Path

import pytest

from myserver import cli


def test_serve_wires_args_through(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_serve(*, host: str, port: int, ledger_path: Path) -> None:
        captured.update(host=host, port=port, ledger_path=ledger_path)

    monkeypatch.setattr(cli, "serve", fake_serve)
    rc = cli.main(["serve", "--host", "0.0.0.0", "--port", "9000", "--ledger", "/tmp/l.jsonl"])
    assert rc == 0
    assert captured == {"host": "0.0.0.0", "port": 9000, "ledger_path": Path("/tmp/l.jsonl")}


def test_serve_defaults_to_localhost(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(cli, "serve", lambda **kw: captured.update(kw))
    cli.main(["serve"])
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8787


def test_no_subcommand_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit):
        cli.main([])
