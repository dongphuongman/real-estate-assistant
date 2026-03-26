"""
SPRAV Defect Tracker

Manages defect logging, severity classification, and tracking.

Usage:
    from scripts.sprav.defect_tracker import DefectTracker, Defect, Severity, Priority

    tracker = DefectTracker()
    tracker.add_defect(
        title="API returns 500 on invalid input",
        severity=Severity.HIGH,
        priority=Priority.P1,
        component="API",
        description="POST /api/v1/search returns 500 when query is empty",
    )
    tracker.save("defects.json")
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class Severity(str, Enum):
    """Defect severity levels."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    ENHANCEMENT = "Enhancement"


class Priority(str, Enum):
    """Defect priority levels."""

    P1 = "P1"  # Fix immediately
    P2 = "P2"  # Fix before release
    P3 = "P3"  # Fix in next release
    P4 = "P4"  # Fix when possible


class Status(str, Enum):
    """Defect status."""

    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    FIXED = "Fixed"
    VERIFIED = "Verified"
    DEFERRED = "Deferred"
    WONT_FIX = "Won't Fix"
    DUPLICATE = "Duplicate"


@dataclass
class Defect:
    """Represents a single defect."""

    id: str
    title: str
    severity: Severity
    priority: Priority
    component: str
    description: str
    status: Status = Status.OPEN
    owner: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    steps_to_reproduce: list[str] = field(default_factory=list)
    expected_behavior: str = ""
    actual_behavior: str = ""
    environment: str = ""
    evidence: list[str] = field(default_factory=list)
    related_defects: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            **asdict(self),
            "severity": self.severity.value,
            "priority": self.priority.value,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Defect":
        """Create from dictionary."""
        data["severity"] = Severity(data["severity"])
        data["priority"] = Priority(data["priority"])
        data["status"] = Status(data["status"])
        return cls(**data)


class DefectTracker:
    """
    Manages defect tracking for SPRAV validation.

    Supports adding, updating, querying, and exporting defects.
    """

    def __init__(self, project_root: Path | None = None):
        """
        Initialize the defect tracker.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.defects: list[Defect] = []
        self._counter = 0

    def _generate_id(self) -> str:
        """Generate a unique defect ID."""
        self._counter += 1
        return f"D{self._counter:03d}"

    def add_defect(
        self,
        title: str,
        severity: Severity,
        priority: Priority,
        component: str,
        description: str,
        owner: str = "",
        steps_to_reproduce: list[str] | None = None,
        expected_behavior: str = "",
        actual_behavior: str = "",
        environment: str = "",
        evidence: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> Defect:
        """
        Add a new defect.

        Args:
            title: Short defect title
            severity: Severity level
            priority: Priority level
            component: Affected component
            description: Detailed description
            owner: Person responsible
            steps_to_reproduce: List of steps
            expected_behavior: What should happen
            actual_behavior: What actually happens
            environment: Environment details
            evidence: Supporting evidence
            tags: Tags for categorization

        Returns:
            The created defect
        """
        defect = Defect(
            id=self._generate_id(),
            title=title,
            severity=severity,
            priority=priority,
            component=component,
            description=description,
            owner=owner,
            steps_to_reproduce=steps_to_reproduce or [],
            expected_behavior=expected_behavior,
            actual_behavior=actual_behavior,
            environment=environment,
            evidence=evidence or [],
            tags=tags or [],
        )
        self.defects.append(defect)
        return defect

    def get_defect(self, defect_id: str) -> Defect | None:
        """Get a defect by ID."""
        for defect in self.defects:
            if defect.id == defect_id:
                return defect
        return None

    def update_defect(
        self,
        defect_id: str,
        status: Status | None = None,
        owner: str | None = None,
        **kwargs,
    ) -> Defect | None:
        """
        Update a defect.

        Args:
            defect_id: ID of the defect to update
            status: New status
            owner: New owner
            **kwargs: Other fields to update

        Returns:
            The updated defect or None if not found
        """
        defect = self.get_defect(defect_id)
        if defect is None:
            return None

        if status is not None:
            defect.status = status
        if owner is not None:
            defect.owner = owner

        for key, value in kwargs.items():
            if hasattr(defect, key):
                setattr(defect, key, value)

        defect.updated_at = datetime.now().isoformat()
        return defect

    def query(
        self,
        severity: Severity | None = None,
        priority: Priority | None = None,
        status: Status | None = None,
        component: str | None = None,
        owner: str | None = None,
        tag: str | None = None,
    ) -> list[Defect]:
        """
        Query defects by various criteria.

        Args:
            severity: Filter by severity
            priority: Filter by priority
            status: Filter by status
            component: Filter by component
            owner: Filter by owner
            tag: Filter by tag

        Returns:
            List of matching defects
        """
        results = self.defects

        if severity is not None:
            results = [d for d in results if d.severity == severity]
        if priority is not None:
            results = [d for d in results if d.priority == priority]
        if status is not None:
            results = [d for d in results if d.status == status]
        if component is not None:
            results = [d for d in results if d.component == component]
        if owner is not None:
            results = [d for d in results if d.owner == owner]
        if tag is not None:
            results = [d for d in results if tag in d.tags]

        return results

    @property
    def critical_count(self) -> int:
        """Count of critical defects."""
        return len(self.query(severity=Severity.CRITICAL))

    @property
    def high_count(self) -> int:
        """Count of high severity defects."""
        return len(self.query(severity=Severity.HIGH))

    @property
    def open_count(self) -> int:
        """Count of open defects."""
        return len(self.query(status=Status.OPEN))

    @property
    def blocker_count(self) -> int:
        """Count of blockers (Critical or High + P1/P2)."""
        blockers = [
            d
            for d in self.defects
            if d.severity in (Severity.CRITICAL, Severity.HIGH)
            and d.priority in (Priority.P1, Priority.P2)
            and d.status == Status.OPEN
        ]
        return len(blockers)

    def save(self, path: Path | str) -> None:
        """
        Save defects to a file.

        Args:
            path: Output file path (.json or .csv)
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.suffix == ".json":
            with open(path, "w") as f:
                json.dump([d.to_dict() for d in self.defects], f, indent=2)
        elif path.suffix == ".csv":
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "ID",
                        "Title",
                        "Severity",
                        "Priority",
                        "Component",
                        "Status",
                        "Owner",
                        "Description",
                        "Created",
                        "Updated",
                    ]
                )
                for d in self.defects:
                    writer.writerow(
                        [
                            d.id,
                            d.title,
                            d.severity.value,
                            d.priority.value,
                            d.component,
                            d.status.value,
                            d.owner,
                            d.description,
                            d.created_at,
                            d.updated_at,
                        ]
                    )
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    def load(self, path: Path | str) -> None:
        """
        Load defects from a file.

        Args:
            path: Input file path (.json)
        """
        path = Path(path)
        if path.suffix == ".json":
            with open(path) as f:
                data = json.load(f)
            self.defects = [Defect.from_dict(d) for d in data]
            # Update counter to avoid ID collisions
            if self.defects:
                max_id = max(int(d.id[1:]) for d in self.defects)
                self._counter = max_id
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    def summary(self) -> dict:
        """
        Generate a summary of defects.

        Returns:
            Dictionary with defect statistics
        """
        return {
            "total": len(self.defects),
            "by_severity": {s.value: len(self.query(severity=s)) for s in Severity},
            "by_priority": {p.value: len(self.query(priority=p)) for p in Priority},
            "by_status": {s.value: len(self.query(status=s)) for s in Status},
            "blockers": self.blocker_count,
            "critical_open": len(
                self.query(severity=Severity.CRITICAL, status=Status.OPEN)
            ),
            "high_open": len(self.query(severity=Severity.HIGH, status=Status.OPEN)),
        }

    def to_markdown(self) -> str:
        """
        Generate markdown table of defects.

        Returns:
            Markdown formatted string
        """
        if not self.defects:
            return "No defects logged."

        lines = [
            "# Defect Log",
            "",
            f"**Total Defects:** {len(self.defects)}",
            f"**Blockers:** {self.blocker_count}",
            "",
            "| ID | Title | Severity | Priority | Component | Status | Owner |",
            "|----|-------|----------|----------|-----------|--------|-------|",
        ]

        # Sort by severity, then priority
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
        }
        priority_order = {
            Priority.P1: 0,
            Priority.P2: 1,
            Priority.P3: 2,
            Priority.P4: 3,
        }

        sorted_defects = sorted(
            self.defects,
            key=lambda d: (
                severity_order.get(d.severity, 99),
                priority_order.get(d.priority, 99),
            ),
        )

        for d in sorted_defects:
            lines.append(
                f"| {d.id} | {d.title} | {d.severity.value} | {d.priority.value} | {d.component} | {d.status.value} | {d.owner} |"
            )

        return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for defect tracker."""
    import argparse

    parser = argparse.ArgumentParser(description="SPRAV Defect Tracker")
    parser.add_argument("--load", type=Path, help="Load defects from file")
    parser.add_argument("--save", type=Path, help="Save defects to file")
    parser.add_argument("--summary", action="store_true", help="Print summary")
    parser.add_argument("--markdown", action="store_true", help="Output as markdown")

    args = parser.parse_args(argv)

    tracker = DefectTracker()

    if args.load:
        tracker.load(args.load)
        print(f"Loaded {len(tracker.defects)} defects from {args.load}")

    if args.summary:
        print(json.dumps(tracker.summary(), indent=2))

    if args.markdown:
        print(tracker.to_markdown())

    if args.save:
        tracker.save(args.save)
        print(f"Saved {len(tracker.defects)} defects to {args.save}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
