# my-server

[![CI](https://github.com/MyThingsLab/my-server/actions/workflows/ci.yml/badge.svg)](https://github.com/MyThingsLab/my-server/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/MyThingsLab/my-server/branch/main/graph/badge.svg)](https://codecov.io/gh/MyThingsLab/my-server)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![MIT](https://img.shields.io/badge/license-MIT-green)

A [MyThingsLab](../my-things-core) `My[X]` tool that **surfaces the fleet over
HTTP**. It is the one tool that also runs as a long-lived process
(`myserver serve`) while staying a normal CLI, so CI, the shared ledger, and the
Engine seam all still apply.

This first cut is a **read-only ledger server**: a small, dependency-free HTTP
server (Python's `http.server`, no framework) that exposes the shared ledger so
the fleet's history can be watched from a browser or `curl`. It never mutates
anything — the only writes it makes are its own `serve` provenance records. A
second transport, `myserver mcp`, exposes the same read-only + one-write
surface to MCP clients over stdio; it's the one place `my-server` pulls in a
third-party dependency (the `mcp` SDK) — everything else stays stdlib.

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
  -d '{"repo":"MyThingsLab/my-things-core","title":"Study GNNs","body":"depth first"}'
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

## MCP

```bash
myserver mcp --ledger .mythings/ledger.jsonl   # speaks JSON-RPC over stdio
```

Same four capabilities as the HTTP API, as MCP tools: `list_tools`,
`tool_status`, `read_ledger`, `enqueue_issue`. It's a second transport over the
same `App` — no separate auth model: `enqueue_issue` is gated by `MYSERVER_TOKEN`
in the server process's own environment exactly like the HTTP `POST`, and is
disabled the same way if it's unset. Point any MCP client at it by launching
`myserver mcp` as a subprocess, e.g. in Claude Desktop's config:

```json
{
  "mcpServers": {
    "mythingslab": {
      "command": "myserver",
      "args": ["mcp", "--ledger", "/path/to/.mythings/ledger.jsonl"],
      "env": { "MYSERVER_TOKEN": "..." }
    }
  }
}
```

## Roadmap

The skeleton keeps growing on the same socket-free `App` router — next up: a
status **dashboard** rendering ledger/PR/fleet state.

## Install (development)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ../my-things-core -e ".[dev]"
pytest
```

## License

MIT — see [`LICENSE`](LICENSE).
