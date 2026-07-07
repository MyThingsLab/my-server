# my-server

[![CI](https://github.com/MyThingsLab/my-server/actions/workflows/ci.yml/badge.svg)](https://github.com/MyThingsLab/my-server/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/MyThingsLab/my-server/branch/main/graph/badge.svg)](https://codecov.io/gh/MyThingsLab/my-server)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![MIT](https://img.shields.io/badge/license-MIT-green)

A [MyThingsLab](../mythings-core) `My[X]` tool that **surfaces the fleet over
HTTP**. It is the one tool that also runs as a long-lived process
(`myserver serve`) while staying a normal CLI, so CI, the shared ledger, and the
Engine seam all still apply.

This first cut is a **read-only ledger server**: a small, dependency-free HTTP
server (Python's `http.server`, no framework) that exposes the shared ledger so
the fleet's history can be watched from a browser or `curl`. It never mutates
anything — the only writes it makes are its own `serve` provenance records.

## Endpoints

| Method | Path      | Returns                                                        |
|--------|-----------|---------------------------------------------------------------|
| `GET`  | `/health` | `{"status":"ok","tool":"my-server","version":…}`              |
| `GET`  | `/`       | same as `/health`                                             |
| `GET`  | `/ledger` | recent ledger entries — `?tool=`, `?kind=`, `?limit=` filters |

Any non-`GET` verb returns `405` — the server is read-only.

## Run

```bash
myserver serve                       # http://127.0.0.1:8787
myserver serve --port 9000 --ledger .mythings/ledger.jsonl
```

It binds to `127.0.0.1` by default; exposing it beyond localhost (`--host`) is an
explicit opt-in.

## Roadmap

The skeleton is shaped to grow, layering onto the same socket-free `App` router:

- an HTTP/JSON API over the other tools (delegating to *their* Engine calls),
- an **MCP server** exposing the contracts to agents,
- a status **dashboard** rendering ledger/PR/fleet state.

## Install (development)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ../mythings-core -e ".[dev]"
pytest
```

## License

MIT — see [`LICENSE`](LICENSE).
