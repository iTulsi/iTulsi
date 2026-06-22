#!/usr/bin/env python3
"""Update the Recent Engineering Activity section in README.md."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

USERNAME = "iTulsi"
README_PATH = Path(__file__).resolve().parents[1] / "README.md"
START_MARKER = "<!--START_SECTION:activity-->"
END_MARKER = "<!--END_SECTION:activity-->"
MAX_ITEMS = 6


def github_request(url: str) -> list[dict[str, Any]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-activity-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    token = os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        print(f"GitHub API returned HTTP {error.code}: {error.reason}", file=sys.stderr)
        raise
    except urllib.error.URLError as error:
        print(f"Unable to reach GitHub API: {error.reason}", file=sys.stderr)
        raise


def format_date(value: str) -> str:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return timestamp.astimezone(timezone.utc).strftime("%d %b %Y")


def describe_event(event: dict[str, Any]) -> str | None:
    event_type = event.get("type", "")
    repo = event.get("repo", {}).get("name", "")
    payload = event.get("payload", {})
    created_at = format_date(event.get("created_at", ""))

    if not repo:
        return None

    repo_link = f"[`{repo}`](https://github.com/{repo})"

    if event_type == "PushEvent":
        commits = payload.get("commits", [])
        count = len(commits)
        branch = str(payload.get("ref", "")).replace("refs/heads/", "") or "a branch"
        label = "commit" if count == 1 else "commits"
        return f"| {created_at} | Pushed **{count} {label}** to `{branch}` | {repo_link} |"

    if event_type == "PullRequestEvent":
        action = payload.get("action", "updated")
        pull_request = payload.get("pull_request", {})
        number = pull_request.get("number")
        title = pull_request.get("title", "Pull request")
        url = pull_request.get("html_url", f"https://github.com/{repo}/pulls")
        return f"| {created_at} | {action.title()} PR [#{number}: {title}]({url}) | {repo_link} |"

    if event_type == "IssuesEvent":
        action = payload.get("action", "updated")
        issue = payload.get("issue", {})
        number = issue.get("number")
        title = issue.get("title", "Issue")
        url = issue.get("html_url", f"https://github.com/{repo}/issues")
        return f"| {created_at} | {action.title()} issue [#{number}: {title}]({url}) | {repo_link} |"

    if event_type == "CreateEvent":
        ref_type = payload.get("ref_type", "repository")
        ref = payload.get("ref")
        detail = f" `{ref}`" if ref else ""
        return f"| {created_at} | Created {ref_type}{detail} | {repo_link} |"

    if event_type == "ReleaseEvent":
        action = payload.get("action", "published")
        release = payload.get("release", {})
        name = release.get("name") or release.get("tag_name") or "release"
        url = release.get("html_url", f"https://github.com/{repo}/releases")
        return f"| {created_at} | {action.title()} release [{name}]({url}) | {repo_link} |"

    return None


def build_section(events: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    seen: set[str] = set()

    for event in events:
        row = describe_event(event)
        if not row or row in seen:
            continue
        seen.add(row)
        rows.append(row)
        if len(rows) >= MAX_ITEMS:
            break

    if not rows:
        return "_No recent public activity found yet._"

    return "\n".join(
        [
            "| Date | Activity | Repository |",
            "|---|---|---|",
            *rows,
        ]
    )


def update_readme(section: str) -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        flags=re.DOTALL,
    )
    replacement = f"{START_MARKER}\n{section}\n{END_MARKER}"

    updated, count = pattern.subn(replacement, readme)
    if count != 1:
        raise RuntimeError("Could not find exactly one activity section in README.md")

    README_PATH.write_text(updated, encoding="utf-8")


def main() -> None:
    url = f"https://api.github.com/users/{USERNAME}/events/public?per_page=100"
    events = github_request(url)
    update_readme(build_section(events))
    print("README activity section updated successfully.")


if __name__ == "__main__":
    main()
