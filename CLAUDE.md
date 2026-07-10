# my-server — agent instructions

You are developing **my-server**, a MyThingsLab My[X] tool.

**Inherited rules:** obey [`./HARNESS.md`](./HARNESS.md) in full — the vendored
MyThingsLab build-harness rules. Do not restate or override them. Anything not
covered here defers to `HARNESS.md`, then `my-things-core/docs/CONVENTIONS.md`.

## This tool

- **Purpose:** surfaces the fleet — a read-only view of the shared ledger, plus
  one gated write — over two transports layered on the same socket-free `App`:
  HTTP (`myserver serve`) and MCP over stdio (`myserver mcp`). It is the one
  My[X] tool that also runs as a long-lived process, while staying a normal
  CLI so CI, the ledger, and the Engine seam all still apply. Planned next:
  a status dashboard, same `App` underneath.
- **The single Engine call:** none yet — the server is deterministic. It never
  adds its own model call; when the API layer surfaces another tool's capability
  it delegates to *that* tool's Engine call, keeping the "one Engine call per
  judgment step" contract intact.
- **Invariants / rules:** read-only over the ledger and repo state, with exactly
  **one** deliberate write: `POST /tools/<name>/issues` (HTTP) / `enqueue_issue`
  (MCP) enqueues a labeled backlog issue that the target tool's own CI loop
  picks up. That write never opens a PR and never spends model tokens — it only
  files an issue. It is **fail-closed**: disabled unless `MYSERVER_TOKEN` is set
  in the server process's environment, and every request must carry it (HTTP:
  `Authorization: Bearer <token>`; MCP: the MCP layer attaches the same token
  itself, since MCP calls carry no headers) — no unauthenticated mutation,
  ever. The server may append its **own** provenance to the ledger (`serve`,
  `enqueue`) but never mutates other tools' entries. HTTP binds `127.0.0.1` by
  default (beyond-localhost is an explicit opt-in); MCP is stdio-only, no
  network exposure at all. `mcp` (the SDK) is the one third-party runtime
  dependency beyond `my-things-core` — everything else here is stdlib.
- **Backlog label:** `my-server`
