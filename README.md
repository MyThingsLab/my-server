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

### Read (always available)

| Method | Path             | Returns                                                        |
|--------|------------------|---------------------------------------------------------------|
| `GET`  | `/health`, `/`   | `{"status":"ok","tool":"my-server","version":…}`              |
| `GET`  | `/ledger`        | recent ledger entries — `?tool=`, `?kind=`, `?limit=` filters |
| `GET`  | `/tools`         | the tools the API can enqueue work for                        |
| `GET`  | `/tools/<name>`  | one tool's `{name, label, summary}`                           |

### Enqueue (the one write — gated, off by default)

| Method | Path                    | Effect                                                  |
|--------|-------------------------|---------------------------------------------------------|
| `POST` | `/tools/<name>/issues`  | files a backlog issue labeled `<name>` in a target repo |

`POST` **never opens a PR and never spends model tokens** — it only files a
labeled issue that the target tool's own CI loop then picks up. Following the
fleet convention (each tool's backlog label is its own name), the tool acts on
the issue on its normal schedule.

The write is **fail-closed**: it is disabled unless `MYSERVER_TOKEN` is set in
the server's environment, and every request must carry `Authorization: Bearer
<token>`. Body is JSON — `repo` and `title` are required, `body` optional:

```bash
export MYSERVER_TOKEN=$(openssl rand -hex 16)
myserver serve                       # prints "enqueue enabled"

curl -X POST http://127.0.0.1:8787/tools/my-researcher/issues \
  -H "Authorization: Bearer $MYSERVER_TOKEN" \
  -d '{"repo":"MyThingsLab/mythings-core","title":"Study GNNs","body":"depth first"}'
# → 201 {"tool":"my-researcher","label":"my-researcher","repo":…,"issue":7,"url":…}
```

Every enqueue is recorded to the server's own ledger (`kind:"enqueue"`) for audit.

## Run

```bash
myserver serve                       # http://127.0.0.1:8787
myserver serve --port 9000 --ledger .mythings/ledger.jsonl
```

It binds to `127.0.0.1` by default; exposing it beyond localhost (`--host`) is an
explicit opt-in.

## Roadmap

The skeleton keeps growing on the same socket-free `App` router:

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
