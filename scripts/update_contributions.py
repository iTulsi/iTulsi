#!/usr/bin/env python3
"""Update the profile README with the user's latest public pull requests."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

USERNAME = "iTulsi"
README_PATH = Path("README.md")
START_MARKER = "<!--START_SECTION:contributions-->"
END_MARKER = "<!--END_SECTION:contributions-->"
GRAPHQL_URL = "https://api.github.com/graphql"
MAX_PULL_REQUESTS = 6

QUERY = """
query($searchQuery: String!, $count: Int!) {
  search(query: $searchQuery, type: ISSUE, first: $count) {
    nodes {
      ... on PullRequest {
        number
        title
        url
        state
        mergedAt
        repository {
          nameWithOwner
        }
      }
    }
  }
}
"""


def markdown_escape(value: object) -> str:
    """Escape values that would otherwise break a Markdown table."""
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def shorten(value: str, limit: int = 76) -> str:
    """Keep table rows readable on narrow GitHub layouts."""
    value = " ".join(value.split())
    if len(value) <= limit:
        return value
    return f"{value[: limit - 1].rstrip()}…"


def fetch_pull_requests(token: str) -> list[dict[str, Any]]:
    """Fetch the latest public pull requests authored by the profile owner."""
    if not token.strip():
        raise ValueError("GITHUB_TOKEN is required")

    payload = json.dumps(
        {
            "query": QUERY,
            "variables": {
                "searchQuery": (
                    f"author:{USERNAME} is:pr -repo:{USERNAME}/{USERNAME} "
                    "sort:updated-desc"
                ),
                "count": MAX_PULL_REQUESTS,
            },
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "itulsiprofile-readme-updater",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed: {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Unable to reach GitHub API: {exc.reason}") from exc

    if result.get("errors"):
        raise RuntimeError(f"GitHub GraphQL errors: {result['errors']}")

    nodes = result.get("data", {}).get("search", {}).get("nodes", [])
    return [node for node in nodes if isinstance(node, dict)]


def pull_request_status(pull_request: dict[str, Any]) -> str:
    """Return a human-readable status without duplicating opened/merged events."""
    if pull_request.get("mergedAt"):
        return "Merged"
    return str(pull_request.get("state", "Unknown")).title()


def make_table(pull_requests: list[dict[str, Any]]) -> str:
    """Create the Markdown table inserted into the README."""
    lines = [
        "| Pull Request | Repository | Status |",
        "| --- | --- | --- |",
    ]

    for pull_request in pull_requests:
        title = markdown_escape(shorten(str(pull_request.get("title", "Untitled"))))
        number = pull_request.get("number", "?")
        url = pull_request.get("url", "#")
        repository = markdown_escape(
            pull_request.get("repository", {}).get("nameWithOwner", "Unknown")
        )
        status = pull_request_status(pull_request)
        lines.append(
            f"| [#{number} {title}]({url}) | `{repository}` | {status} |"
        )

    if not pull_requests:
        lines.append("| No public pull requests found yet | - | - |")

    return "\n".join(lines)


def replace_section(content: str, replacement: str) -> str:
    """Replace exactly one marked README section."""
    if content.count(START_MARKER) != 1 or content.count(END_MARKER) != 1:
        raise ValueError("README must contain exactly one contributions marker pair")

    start_index = content.index(START_MARKER) + len(START_MARKER)
    end_index = content.index(END_MARKER)

    if start_index > end_index:
        raise ValueError("README contribution markers are in the wrong order")

    return (
        f"{content[:start_index]}\n"
        f"{replacement.rstrip()}\n"
        f"{content[end_index:]}"
    )


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN", "")
    pull_requests = fetch_pull_requests(token)
    current = README_PATH.read_text(encoding="utf-8")
    updated = replace_section(current, make_table(pull_requests))

    if updated != current:
        README_PATH.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
