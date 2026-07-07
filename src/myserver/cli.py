from __future__ import annotations

import argparse
from pathlib import Path

from myserver.server import serve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="myserver",
        description="A small read-only HTTP server surfacing the MyThingsLab ledger.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    srv = sub.add_parser("serve", help="run the HTTP server (long-lived)")
    srv.add_argument("--host", default="127.0.0.1", help="bind address (default: localhost)")
    srv.add_argument("--port", type=int, default=8787, help="bind port (default: 8787)")
    srv.add_argument(
        "--ledger", type=Path, default=Path(".mythings/ledger.jsonl"), help="ledger to serve"
    )

    args = parser.parse_args(argv)
    if args.cmd == "serve":
        serve(host=args.host, port=args.port, ledger_path=args.ledger)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
