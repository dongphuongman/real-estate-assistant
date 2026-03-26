"""
SPRAV Report Generator

Generates comprehensive SPRAV reports in various formats.

Usage:
    python scripts/sprav/generate_report.py --input results.json --output report.md
    python scripts/sprav/generate_report.py --input results.json --output report.html
    python scripts/sprav/generate_report.py --input results.json --output report.pdf
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def generate_markdown_report(data: dict) -> str:
    """Generate markdown report from validation data."""
    lines = [
        f"# SPRAV Report: {data.get('release_version', 'Unknown')}",
        "",
        f"**Date:** {data.get('timestamp', datetime.now().isoformat())}",
        f"**Release:** {data.get('release_version', 'Unknown')}",
        f"**Overall Status:** {data.get('overall_status', 'Unknown')}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        f"- **Total Validations:** {len(data.get('results', []))}",
        f"- **Passed:** {data.get('passed', 0)}",
        f"- **Failed:** {data.get('failed', 0)}",
        f"- **Blockers:** {data.get('blockers', 0)}",
        f"- **Warnings:** {data.get('warnings', 0)}",
        f"- **Skipped:** {data.get('skipped', 0)}",
        "",
        "### Recommendation",
        "",
        f"**{data.get('recommendation', 'No recommendation available')}**",
        "",
        "---",
        "",
        "## Validation Results Matrix",
        "",
        "| Role | Validation | Status | Description |",
        "|------|------------|--------|-------------|",
    ]

    status_icons = {
        "PASSED": "✅",
        "FAILED": "❌",
        "BLOCKER": "🚫",
        "WARNING": "⚠️",
        "SKIPPED": "⊘",
    }

    for result in data.get("results", []):
        icon = status_icons.get(result.get("status", ""), "")
        lines.append(
            f"| {result.get('role', '-')} | {result.get('name', '-')} | {icon} {result.get('status', '-')} | {result.get('description', '-')} |"
        )

    # Evidence section
    lines.extend(
        [
            "",
            "---",
            "",
            "## Test Evidence",
            "",
        ]
    )

    for result in data.get("results", []):
        evidence = result.get("evidence", [])
        if evidence:
            lines.append(f"### {result.get('name', 'Validation')}")
            lines.append("")
            for item in evidence:
                lines.append(f"- {item}")
            lines.append("")

    # Defects section
    defects_found = any(r.get("defects") for r in data.get("results", []))
    if defects_found:
        lines.extend(
            [
                "---",
                "",
                "## Defect Log",
                "",
                "| ID | Severity | Priority | Component | Description | Status |",
                "|----|----------|----------|-----------|-------------|--------|",
            ]
        )
        defect_id = 1
        for result in data.get("results", []):
            for defect in result.get("defects", []):
                severity = "High" if result.get("status") == "BLOCKER" else "Medium"
                lines.append(
                    f"| D{defect_id:03d} | {severity} | P2 | {result.get('name', '-')} | {defect} | Open |"
                )
                defect_id += 1

    # Go/No-Go criteria
    lines.extend(
        [
            "",
            "---",
            "",
            "## GO Criteria Checklist",
            "",
        ]
    )

    go_criteria = data.get(
        "go_criteria",
        [
            "All automated tests pass (`make ci` succeeds)",
            "No Critical or High severity defects open",
            "Coverage gates met (90% unit, 70% integration)",
            "Security scans pass (0 secrets, 0 high-confidence issues)",
            "Docker deployment succeeds with health checks",
            "Core user journeys validated",
        ],
    )

    for criterion in go_criteria:
        lines.append(f"- [ ] {criterion}")

    lines.extend(
        [
            "",
            "## NO-GO Criteria Checklist",
            "",
        ]
    )

    no_go_criteria = data.get(
        "no_go_criteria",
        [
            "Any Critical defect unresolved",
            "Security vulnerability with known exploit",
            "Coverage below thresholds",
            "Docker deployment fails",
            "Core functionality broken",
        ],
    )

    for criterion in no_go_criteria:
        lines.append(f"- [ ] {criterion}")

    # Sign-off section
    lines.extend(
        [
            "",
            "---",
            "",
            "## Sign-Off",
            "",
            "| Role | Name | Signature | Date |",
            "|------|------|-----------|------|",
            "| Team Lead | | | |",
            "| Architect | | | |",
            "| QA Engineer | | | |",
            "| Business Analyst | | | |",
            "| Automation Engineer | | | |",
            "| Frontend Developer | | | |",
            "| Backend Developer | | | |",
            "",
            "---",
            "",
            f"*Generated by SPRAV Framework v1.0.0 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ]
    )

    return "\n".join(lines)


def generate_html_report(data: dict) -> str:
    """Generate HTML report from validation data."""
    status_colors = {
        "PASSED": "#28a745",
        "FAILED": "#dc3545",
        "BLOCKER": "#721c24",
        "WARNING": "#ffc107",
        "SKIPPED": "#6c757d",
    }

    # Build results table rows
    rows = []
    for result in data.get("results", []):
        status = result.get("status", "UNKNOWN")
        color = status_colors.get(status, "#6c757d")
        rows.append(f"""
            <tr>
                <td>{result.get("role", "-")}</td>
                <td>{result.get("name", "-")}</td>
                <td style="background-color: {color}; color: white;">{status}</td>
                <td>{result.get("description", "-")}</td>
            </tr>
        """)

    # Build evidence sections
    evidence_sections = []
    for result in data.get("results", []):
        evidence = result.get("evidence", [])
        if evidence:
            items = "\n".join(f"<li>{item}</li>" for item in evidence)
            evidence_sections.append(f"""
                <div class="evidence-section">
                    <h4>{result.get("name", "Validation")}</h4>
                    <ul>{items}</ul>
                </div>
            """)

    # Build defect rows
    defect_rows = []
    defect_id = 1
    for result in data.get("results", []):
        for defect in result.get("defects", []):
            severity = "High" if result.get("status") == "BLOCKER" else "Medium"
            defect_rows.append(f"""
                <tr>
                    <td>D{defect_id:03d}</td>
                    <td>{severity}</td>
                    <td>P2</td>
                    <td>{result.get("name", "-")}</td>
                    <td>{defect}</td>
                    <td>Open</td>
                </tr>
            """)
            defect_id += 1

    defect_section = ""
    if defect_rows:
        defect_section = f"""
            <h2>Defect Log</h2>
            <table class="defect-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Severity</th>
                        <th>Priority</th>
                        <th>Component</th>
                        <th>Description</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(defect_rows)}
                </tbody>
            </table>
        """

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SPRAV Report: {data.get("release_version", "Unknown")}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .summary-card {{
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            background-color: #f8f9fa;
        }}
        .summary-card.passed {{ background-color: #d4edda; }}
        .summary-card.failed {{ background-color: #f8d7da; }}
        .summary-card.blocker {{ background-color: #f5c6cb; }}
        .summary-card.warning {{ background-color: #fff3cd; }}
        .summary-card h3 {{ margin: 0; font-size: 2em; }}
        .summary-card p {{ margin: 5px 0 0; color: #666; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #007bff;
            color: white;
        }}
        tr:hover {{ background-color: #f5f5f5; }}
        .recommendation {{
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            font-size: 1.2em;
        }}
        .recommendation.go {{ background-color: #d4edda; color: #155724; }}
        .recommendation.no-go {{ background-color: #f8d7da; color: #721c24; }}
        .recommendation.conditional {{ background-color: #fff3cd; color: #856404; }}
        .checklist {{ list-style: none; padding: 0; }}
        .checklist li {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
        .checklist li:before {{ content: '☐ '; margin-right: 8px; }}
        .sign-off-table td {{ width: 25%; }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>SPRAV Report: {data.get("release_version", "Unknown")}</h1>

        <p><strong>Date:</strong> {
        data.get("timestamp", datetime.now().isoformat())
    }</p>
        <p><strong>Release:</strong> {data.get("release_version", "Unknown")}</p>
        <p><strong>Overall Status:</strong> <strong>{
        data.get("overall_status", "Unknown")
    }</strong></p>

        <div class="summary-grid">
            <div class="summary-card passed">
                <h3>{data.get("passed", 0)}</h3>
                <p>Passed</p>
            </div>
            <div class="summary-card failed">
                <h3>{data.get("failed", 0)}</h3>
                <p>Failed</p>
            </div>
            <div class="summary-card blocker">
                <h3>{data.get("blockers", 0)}</h3>
                <p>Blockers</p>
            </div>
            <div class="summary-card warning">
                <h3>{data.get("warnings", 0)}</h3>
                <p>Warnings</p>
            </div>
        </div>

        <div class="recommendation {
        "go"
        if data.get("overall_status") == "PASSED"
        else "no-go"
        if data.get("overall_status") == "BLOCKER"
        else "conditional"
    }">
            <strong>Recommendation:</strong> {
        data.get("recommendation", "No recommendation available")
    }
        </div>

        <h2>Validation Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Role</th>
                    <th>Validation</th>
                    <th>Status</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>

        <h2>Test Evidence</h2>
        {"".join(evidence_sections)}

        {defect_section}

        <h2>GO Criteria</h2>
        <ul class="checklist">
            {
        "".join(
            f"<li>{c}</li>"
            for c in data.get(
                "go_criteria",
                [
                    "All automated tests pass",
                    "No Critical or High severity defects open",
                    "Coverage gates met",
                    "Security scans pass",
                    "Docker deployment succeeds",
                    "Core user journeys validated",
                ],
            )
        )
    }
        </ul>

        <h2>NO-GO Criteria</h2>
        <ul class="checklist">
            {
        "".join(
            f"<li>{c}</li>"
            for c in data.get(
                "no_go_criteria",
                [
                    "Any Critical defect unresolved",
                    "Security vulnerability with known exploit",
                    "Coverage below thresholds",
                    "Docker deployment fails",
                    "Core functionality broken",
                ],
            )
        )
    }
        </ul>

        <h2>Sign-Off</h2>
        <table class="sign-off-table">
            <thead>
                <tr>
                    <th>Role</th>
                    <th>Name</th>
                    <th>Signature</th>
                    <th>Date</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>Team Lead</td><td></td><td></td><td></td></tr>
                <tr><td>Architect</td><td></td><td></td><td></td></tr>
                <tr><td>QA Engineer</td><td></td><td></td><td></td></tr>
                <tr><td>Business Analyst</td><td></td><td></td><td></td></tr>
                <tr><td>Automation Engineer</td><td></td><td></td><td></td></tr>
                <tr><td>Frontend Developer</td><td></td><td></td><td></td></tr>
                <tr><td>Backend Developer</td><td></td><td></td><td></td></tr>
            </tbody>
        </table>

        <div class="footer">
            Generated by SPRAV Framework v1.0.0 on {
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
        </div>
    </div>
</body>
</html>
    """

    return html


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="SPRAV Report Generator")
    parser.add_argument(
        "--input", "-i", type=Path, required=True, help="Input JSON file"
    )
    parser.add_argument(
        "--output", "-o", type=Path, required=True, help="Output file (.md or .html)"
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["markdown", "html"],
        help="Output format (auto-detected from extension)",
    )

    args = parser.parse_args(argv)

    # Load input data
    with open(args.input) as f:
        data = json.load(f)

    # Determine format
    if args.format:
        fmt = args.format
    elif args.output.suffix in (".md", ".markdown"):
        fmt = "markdown"
    elif args.output.suffix in (".html", ".htm"):
        fmt = "html"
    else:
        print(
            f"Warning: Unknown extension '{args.output.suffix}', defaulting to markdown"
        )
        fmt = "markdown"

    # Generate report
    if fmt == "markdown":
        content = generate_markdown_report(data)
    else:
        content = generate_html_report(data)

    # Write output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        f.write(content)

    print(f"Report generated: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
