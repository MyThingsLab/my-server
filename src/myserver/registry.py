from __future__ import annotations

from dataclasses import dataclass

# The tools the API can enqueue work for. Fleet convention (each tool's CLAUDE.md
# "Backlog label" seam): a tool's backlog label == its own name, and it picks up
# issues carrying that label through its normal CI loop. Enqueuing is therefore
# uniform — create a labeled issue; the tool's loop does the rest. my-orchestrator
# has no label of its own (it reads every backlog), so it is not enqueue-able.


@dataclass(frozen=True)
class ToolSpec:
    name: str
    label: str
    summary: str


REGISTRY: tuple[ToolSpec, ...] = (
    ToolSpec("my-researcher", "my-researcher", "Research a topic into a cited study brief."),
    ToolSpec("my-planner", "my-planner", "Produce a recommended work sequence."),
    ToolSpec("my-projector", "my-projector", "Reconcile the project board with repo state."),
    ToolSpec("my-changelogger", "my-changelogger", "Add a changelog section for recent entries."),
    ToolSpec("my-tester", "my-tester", "Add a test for the first uncovered unit."),
    ToolSpec("my-guard", "my-guard", "Evaluate a proposed action against the rule engine."),
)

_BY_NAME = {spec.name: spec for spec in REGISTRY}


def find(name: str) -> ToolSpec | None:
    return _BY_NAME.get(name)
