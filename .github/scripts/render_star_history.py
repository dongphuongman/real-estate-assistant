#!/usr/bin/env python3
"""Render self-hosted star-history SVGs for the AleksNeStu/ai-real-estate-assistant README.

Pulls star timestamps via the GitHub REST API (paginated), bins them into a
cumulative series, and renders light + dark themed SVGs with matplotlib. The
X-axis is manually thinned to <= 12 labels (first month, last month, every
Jan-1, every quarter start) to avoid overlapping labels that plagued the
previous carsteneu/mystarhistory@v1 action (which hardcoded 800x533 px and
emitted one label per calendar month).

Used by .github/workflows/star-history.yml.
"""

import argparse
import io
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless backend for CI runners

import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import requests  # noqa: E402

API_BASE = "https://api.github.com"
DPI = 100
WIDTH_PX = 1400
HEIGHT_PX = 533
LINE_COLOR = "#fc6d26"

PER_PAGE = 100
RATE_LIMIT_FLOOR = 10


def fetch_stargazers(repo: str, token: str, api_base: str = API_BASE) -> list:
    """Fetch star timestamps (UTC) for `owner/repo`, paginated, sorted ascending.

    Aborts with non-zero exit on any HTTP error. Honors X-RateLimit-Remaining
    (refuses to proceed below RATE_LIMIT_FLOOR).
    """
    url = f"{api_base}/repos/{repo}/stargazers"
    # `application/vnd.github.star+json` is required to get the `starred_at`
    # timestamp on each entry; with the default media type the endpoint
    # returns user objects only (no timestamps).
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.star+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    params = {"per_page": PER_PAGE}
    dates: list = []

    while url:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            print(
                f"ERROR: HTTP {resp.status_code} fetching {url}: {resp.text[:200]}",
                file=sys.stderr,
            )
            sys.exit(1)

        remaining = int(resp.headers.get("X-RateLimit-Remaining", "9999"))
        if remaining < RATE_LIMIT_FLOOR:
            print(
                f"ERROR: rate-limit remaining={remaining}; aborting (floor={RATE_LIMIT_FLOOR})",
                file=sys.stderr,
            )
            sys.exit(1)

        page = resp.json()
        if not isinstance(page, list):
            print(f"ERROR: unexpected payload shape (not a list): {str(page)[:200]}", file=sys.stderr)
            sys.exit(1)

        for entry in page:
            starred_at = entry.get("starred_at")
            if not starred_at:
                continue
            dt = datetime.fromisoformat(starred_at.replace("Z", "+00:00"))
            dates.append(dt.astimezone(timezone.utc))

        # Parse Link header for the next page (URL already carries the query string).
        url = None
        params = {}
        for part in resp.headers.get("Link", "").split(","):
            if 'rel="next"' in part:
                url = part.split(";")[0].strip(" <>")
                break

    dates.sort()
    return dates


def _next_month(dt):
    if dt.month == 12:
        return dt.replace(year=dt.year + 1, month=1)
    return dt.replace(month=dt.month + 1)


def bin_cumulative(dates: list, today: datetime | None = None) -> tuple:
    """Bin star dates into cumulative (xs, ys) at first-of-month boundaries.

    xs: list of first-of-month datetimes from min(star) to today (inclusive).
    ys: cumulative count of stars at each x.
    """
    if not dates:
        raise ValueError("dates is empty")
    today = today or datetime.now(tz=timezone.utc)
    first = dates[0].replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    last_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)

    xs: list = []
    cur = first
    while cur <= last_month:
        xs.append(cur)
        cur = _next_month(cur)

    ys: list = []
    sorted_dates = sorted(dates)
    idx = 0
    for x in xs:
        while idx < len(sorted_dates) and sorted_dates[idx] <= x:
            idx += 1
        ys.append(idx)

    return xs, ys


def select_label_positions(xs: list, max_labels: int = 12) -> list:
    """Pick <=max_labels dates from xs for X-axis tick labels.

    Always includes first xs and last xs. Includes every Jan-1 (year boundary)
    and every quarter start (Apr/Jul/Oct). If still over max_labels, drops
    quarter-starts first; if still too many, takes evenly-spaced positions and
    guarantees the last point is present.
    """
    if not xs:
        return []
    if len(xs) <= max_labels:
        return list(xs)

    candidates = {xs[0], xs[-1]}
    for x in xs:
        if x.month == 1 or x.month in (4, 7, 10):
            candidates.add(x)

    result = sorted(candidates)

    if len(result) > max_labels:
        # Drop quarter-starts before year-boundaries.
        trimmed = [x for x in result if x.month == 1]
        if xs[0] not in trimmed:
            trimmed.insert(0, xs[0])
        if xs[-1] not in trimmed:
            trimmed.append(xs[-1])
        result = sorted(set(trimmed))

    if len(result) > max_labels:
        # Last resort: evenly-spaced slice + guaranteed last point.
        step = max(1, len(result) // max_labels)
        sampled = result[::step][:max_labels]
        if xs[-1] not in sampled:
            sampled[-1] = xs[-1]
        result = sampled

    return result


def render_chart(
    xs: list,
    ys: list,
    label_xs: list,
    theme: str,
    *,
    width_px: int = WIDTH_PX,
    height_px: int = HEIGHT_PX,
    title: str = "Star History — AleksNeStu/ai-real-estate-assistant",
) -> bytes:
    """Render a single SVG (theme='light' or 'dark') and return its bytes."""
    is_dark = theme == "dark"
    bg = "#0d1117" if is_dark else "#ffffff"
    text_color = "#c9d1d9" if is_dark else "#24292e"
    grid_color = "#30363d" if is_dark else "#d0d7de"
    edge_color = "#30363d" if is_dark else "#d0d7de"

    fig, ax = plt.subplots(figsize=(width_px / DPI, height_px / DPI), dpi=DPI)
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)

    ax.plot(xs, ys, color=LINE_COLOR, linewidth=2)
    ax.fill_between(xs, ys, color=LINE_COLOR, alpha=0.10)

    ax.set_xticks(label_xs)
    ax.set_xticklabels(
        [d.strftime("%b %Y") for d in label_xs], rotation=0, ha="center"
    )
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    if ys:
        ax.set_ylim(0, ys[-1] * 1.05)
        ax.yaxis.set_major_locator(plt.MaxNLocator(nbins=8, integer=True))

    ax.set_title(title, pad=12, fontsize=13, color=text_color)
    ax.set_ylabel("Cumulative stars", color=text_color)
    ax.grid(True, axis="y", alpha=0.3, color=grid_color)
    ax.tick_params(axis="x", labelsize=10, colors=text_color)
    ax.tick_params(axis="y", labelsize=10, colors=text_color)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(edge_color)
    ax.spines["left"].set_color(edge_color)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "AleksNeStu/ai-real-estate-assistant"))
    # Prefer GH_STAR_TOKEN (a PAT) over GITHUB_TOKEN: since GitHub restricted
    # the stargazers listing endpoint to admins/collaborators in July 2026,
    # the auto-provided GITHUB_TOKEN no longer has access. GH_STAR_TOKEN
    # holds a repo-owner PAT that does.
    p.add_argument(
        "--token",
        default=os.environ.get("GH_STAR_TOKEN") or os.environ.get("GITHUB_TOKEN", ""),
    )
    p.add_argument("--api-base", default=os.environ.get("GITHUB_API_BASE", API_BASE))
    p.add_argument("--out-dir", default=os.environ.get("OUT_DIR", "assets/my-star-history"))
    args = p.parse_args()

    if not args.token:
        print(
            "ERROR: GH_STAR_TOKEN (or GITHUB_TOKEN, or --token) is required",
            file=sys.stderr,
        )
        return 2

    print(f"Fetching stargazers for {args.repo} ...", flush=True)
    dates = fetch_stargazers(args.repo, args.token, args.api_base)
    if not dates:
        print("ERROR: no stargazers returned", file=sys.stderr)
        return 1

    print(
        f"  fetched {len(dates)} stars from {dates[0].date()} to {dates[-1].date()}",
        flush=True,
    )

    xs, ys = bin_cumulative(dates)
    label_xs = select_label_positions(xs, max_labels=12)
    print(
        f"  {len(label_xs)} X-axis labels: "
        + ", ".join(d.strftime("%b %Y") for d in label_xs),
        flush=True,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for theme in ("light", "dark"):
        svg = render_chart(xs, ys, label_xs, theme)
        path = out_dir / f"star-history-{theme}.svg"
        path.write_bytes(svg)
        print(f"  wrote {path} ({len(svg)} bytes)", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
