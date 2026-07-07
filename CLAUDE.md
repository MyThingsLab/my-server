# my-server — agent instructions

You are developing **my-server**, a MyThingsLab My[X] tool.

**Inherited rules:** obey [`./HARNESS.md`](./HARNESS.md) in full — the vendored
MyThingsLab build-harness rules. Do not restate or override them. Anything not
covered here defers to `HARNESS.md`, then `mythings-core/docs/CONVENTIONS.md`.

## This tool

- **Purpose:** a small HTTP server that surfaces the fleet over HTTP — starting
  with a read-only view of the shared ledger. It is the one My[X] tool that also
  runs as a long-lived process (`myserver serve`), while staying a normal CLI so
  CI, the ledger, and the Engine seam all still apply. Planned surfaces, layered
  on this skeleton: an HTTP/JSON API over the tools, an MCP server exposing the
  contracts to agents, and a status dashboard.
- **The single Engine call:** none yet — the server is deterministic. It never
  adds its own model call; when the API layer surfaces another tool's capability
  it delegates to *that* tool's Engine call, keeping the "one Engine call per
  judgment step" contract intact.
- **Invariants / rules:** read-only over the ledger and repo state — the server
  never opens PRs, mutates the ledger, or performs writes on behalf of a caller.
  It binds to `127.0.0.1` by default; exposing it beyond localhost is an explicit
  opt-in. No unauthenticated mutation surface, ever.
- **Backlog label:** `my-server`
