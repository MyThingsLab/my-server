from __future__ import annotations

from collections.abc import Callable

from mythings.github import _gh

# The one write boundary: create a labeled backlog issue. Injected into the App so
# tests mock only this call (same discipline as the fleet's Runner/Fetcher seams).
IssueCreator = Callable[..., str]


def gh_create_issue(*, repo: str, title: str, body: str, label: str) -> str:
    return _gh(
        ["issue", "create", "--repo", repo, "--title", title, "--body", body, "--label", label]
    ).strip()


def issue_number(url: str) -> int | None:
    tail = url.rstrip("/").rsplit("/", 1)[-1]
    return int(tail) if tail.isdigit() else None
