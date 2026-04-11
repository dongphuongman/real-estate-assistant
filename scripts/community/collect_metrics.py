"""Community metrics collection script.

Collects repository metrics from GitHub API and generates
a JSON snapshot and markdown summary.

Usage:
    python scripts/community/collect_metrics.py
    python scripts/community/collect_metrics.py --output docs/community/metrics
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "AleksNeStu/ai-real-estate-assistant")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def _api_get(path: str) -> dict:
    """Make a GitHub API request."""
    import urllib.request
    import urllib.error

    url = f"https://api.github.com{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "metrics-collector",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"WARN: GitHub API error for {path}: {e.code}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"WARN: Request failed for {path}: {e}", file=sys.stderr)
        return {}


def collect_repo_stats() -> dict:
    """Collect basic repository statistics."""
    data = _api_get(f"/repos/{REPO}")
    if not data:
        return {}

    return {
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "watchers": data.get("subscribers_count", 0),
        "open_issues": data.get("open_issues_count", 0),
        "license": data.get("license", {}).get("spdx_id", "Unknown")
        if data.get("license")
        else "Unknown",
        "default_branch": data.get("default_branch", "dev"),
        "language": data.get("language", "Unknown"),
    }


def collect_issue_stats() -> dict:
    """Collect issue statistics."""
    # Open issues by label
    labels = ["bug", "enhancement", "good first issue", "help wanted", "question"]
    label_counts = {}
    for label in labels:
        data = _api_get(f"/repos/{REPO}/issues?labels={label}&state=open&per_page=1")
        # Use Search API for accurate counts
        search = _api_get(
            f"/search/issues?q=repo:{REPO}+label:{label}+is:issue+is:open"
        )
        label_counts[label] = search.get("total_count", 0) if search else len(data)

    return {
        "open_by_label": label_counts,
        "total_open": sum(label_counts.values()),
    }


def collect_pr_stats() -> dict:
    """Collect pull request statistics."""
    open_prs = _api_get(f"/search/issues?q=repo:{REPO}+is:pr+is:open")
    merged_recently = _api_get(f"/search/issues?q=repo:{REPO}+is:pr+is:merged")

    return {
        "open_prs": open_prs.get("total_count", 0) if open_prs else 0,
        "total_merged": merged_recently.get("total_count", 0) if merged_recently else 0,
    }


def collect_contributors() -> dict:
    """Collect contributor statistics."""
    data = _api_get(f"/repos/{REPO}/contributors?per_page=1")
    if not data:
        return {"total": 0}

    # The list endpoint returns all contributors; use the count
    all_contribs = _api_get(f"/repos/{REPO}/contributors?per_page=100")
    total = len(all_contribs) if isinstance(all_contribs, list) else 1

    return {"total": total}


def generate_snapshot(output_dir: str) -> str:
    """Generate a complete metrics snapshot."""
    now = datetime.now(timezone.utc)
    week_id = now.strftime("%Y-W%W")

    snapshot = {
        "collected_at": now.isoformat(),
        "repository": REPO,
        "week": week_id,
        "repo_stats": collect_repo_stats(),
        "issue_stats": collect_issue_stats(),
        "pr_stats": collect_pr_stats(),
        "contributors": collect_contributors(),
    }

    # Write JSON snapshot
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    json_file = output_path / f"{week_id}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    print(f"Snapshot saved: {json_file}")

    # Generate markdown summary
    md = generate_markdown(snapshot)
    md_file = output_path / f"{week_id}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"Summary saved: {md_file}")

    return str(json_file)


def generate_markdown(snapshot: dict) -> str:
    """Generate a markdown summary from snapshot data."""
    week = snapshot["week"]
    collected = snapshot["collected_at"][:10]
    repo = snapshot.get("repo_stats", {})
    issues = snapshot.get("issue_stats", {})
    prs = snapshot.get("pr_stats", {})
    contribs = snapshot.get("contributors", {})

    lines = [
        f"# Community Metrics: {week}",
        "",
        f"**Collected:** {collected}",
        f"**Repository:** {snapshot['repository']}",
        "",
        "## Repository Stats",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Stars | {repo.get('stars', 'N/A')} |",
        f"| Forks | {repo.get('forks', 'N/A')} |",
        f"| Watchers | {repo.get('watchers', 'N/A')} |",
        f"| Open Issues | {repo.get('open_issues', 'N/A')} |",
        f"| Contributors | {contribs.get('total', 'N/A')} |",
        "",
        "## Issues by Label",
        "",
        "| Label | Open Count |",
        "|-------|------------|",
    ]

    for label, count in issues.get("open_by_label", {}).items():
        lines.append(f"| {label} | {count} |")

    lines.extend(
        [
            "",
            "## Pull Requests",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Open PRs | {prs.get('open_prs', 'N/A')} |",
            f"| Total Merged | {prs.get('total_merged', 'N/A')} |",
            "",
            "---",
            "*Auto-generated by community-metrics workflow*",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect community metrics")
    parser.add_argument(
        "--output",
        default="docs/community/metrics",
        help="Output directory for metrics files",
    )
    args = parser.parse_args()

    generate_snapshot(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
